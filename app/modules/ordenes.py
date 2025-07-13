# app/modules/ordenes.py

import io
import re
from datetime import date, datetime, timedelta
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, current_app, Response, jsonify
)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.units import mm
from app.modules.usuarios import require_modulo
from app.utils.cache import get_cached_data, set_cached_data, get_select2_cached_results, cache_select2_results

bp = Blueprint("ordenes", __name__, template_folder="../templates/ordenes")

# Cache optimizado para materiales usando sistema global
def get_cached_materiales(term):
    """Obtiene materiales del cache global si están vigentes"""
    return get_cached_data(f"materiales_{term.lower()}", ttl=300)

def set_cached_materiales(term, results):
    """Guarda materiales en cache global"""
    set_cached_data(f"materiales_{term.lower()}", results)


def parse_monto(x):
    """
    Convierte un string tipo "$1.234.567,89" o "$595.000" a float 1234567.89 o 595000.0.
    Si x es None o cadena vacía, retorna 0.0.
    """
    if not x:
        return 0.0
    # Quitamos todo lo que no sea dígito, coma o punto:
    limpio = re.sub(r'[^\d,\.]', '', x)  # Ej: "$595.000" -> "595.000"
    # Dividimos por coma para detectar parte decimal (formato chileno):
    partes = limpio.split(',')
    if len(partes) > 1:
        # El último segmento es la parte decimal:
        dec = partes[-1]
        ent = ''.join(partes[:-1])    # une todo lo anterior sin puntos
        limpio2 = ent.replace('.', '') + '.' + dec  # ej: "1.234.567,89" -> "1234567.89"
    else:
        # Si no hay coma, quitamos todos los puntos (eran miles):
        limpio2 = partes[0].replace('.', '')  # ej: "595.000" -> "595000"
    try:
        return float(limpio2)
    except ValueError:
        return 0.0


def formato_pesos(valor):
    try:
        return "${:,.0f}".format(float(valor)).replace(",", ".")
    except Exception:
        return valor


@bp.route("/new", methods=["GET", "POST"])
@require_modulo('orden_de_compra')
def new_orden():
    supabase = current_app.config['SUPABASE']

    # --- Datos GET para autocompletar ---
    tipos_entrega = ["30 DIAS","45 DIAS","60 DIAS","90 DIAS","INMEDIATA","OTRO"]
    plazos_pago   = ["CONTADO","30 DIAS","45 DIAS","60 DIAS","90 DIAS","OTRO"]
    
    # Obtener datos para las listas desplegables
    proveedores = supabase.table("proveedores") \
        .select("id,nombre,rut") \
        .order("nombre", desc=False) \
        .execute().data or []
    
    proyectos = supabase.table("proyectos") \
        .select("id,proyecto") \
        .order("proyecto", desc=False) \
        .execute().data or []
    
    trabajadores = supabase.table("trabajadores") \
        .select("id,nombre") \
        .order("nombre", desc=False) \
        .execute().data or []
    
    history = supabase.table("orden_de_compra") \
        .select("descripcion,precio_unitario,orden_compra") \
        .order("orden_compra", desc=True) \
        .execute().data or []

    # Próximo número de OC
    last_num = supabase.table("orden_de_compra") \
        .select("orden_compra") \
        .order("orden_compra", desc=True) \
        .limit(1) \
        .execute().data
    next_num = (int(last_num[0]["orden_compra"]) if last_num else 0) + 1

    # Próximo art_corr global
    last_corr = supabase.table("orden_de_compra") \
        .select("art_corr") \
        .order("art_corr", desc=True) \
        .limit(1) \
        .execute().data
    next_corr = (int(last_corr[0]["art_corr"]) if last_corr else 0) + 1

    if request.method == "POST":
        # --- Leer encabezado ---
        orden_compra    = next_num           # integer, no str()
        hoy             = date.today()
        fecha           = hoy.isoformat()
        mes             = hoy.month
        semana          = hoy.isocalendar()[1]

        proveedor_id    = int(request.form["proveedor_id"])
        tipo_de_entrega = request.form["tipo_entrega"]
        condicion_pago  = request.form["plazo_pago"]
        
        # Nueva lógica: checkbox "incluir_iva" está marcado por defecto
        # Si incluir_iva está marcado = fac_sin_iva = 0 (con IVA)
        # Si incluir_iva NO está marcado = fac_sin_iva = 1 (sin IVA)
        incluir_iva = request.form.get("incluir_iva") is not None
        fac_sin_iva = 0 if incluir_iva else 1
        
        proyecto_id     = int(request.form["proyecto_id"])
        solicitante     = request.form["solicitado_por"]
        
        # Debug: Log del valor en guardado
        print(f"DEBUG SAVE: incluir_iva recibido = {request.form.get('incluir_iva')}")
        print(f"DEBUG SAVE: incluir_iva procesado = {incluir_iva}")
        print(f"DEBUG SAVE: fac_sin_iva calculado = {fac_sin_iva}")
        print(f"DEBUG SAVE: form keys = {list(request.form.keys())}")

        # --- Leer líneas ---
        cods    = request.form.getlist("cod_linea[]")
        descs   = request.form.getlist("desc_linea[]")
        qtys    = request.form.getlist("cant_linea[]")
        netos   = request.form.getlist("neto_linea[]")
        totals  = request.form.getlist("total_linea[]")

        lineas = []
        for cod, desc, qty, net, tot in zip(cods, descs, qtys, netos, totals):
            if cod and float(qty) > 0:
                descripcion = desc  # Usa siempre lo que viene del formulario
                lineas.append([
                    cod,
                    descripcion,
                    int(qty),
                    parse_monto(net),
                    parse_monto(tot)
                ])

        rows = []
        corr = next_corr
        for cod, desc, qty, net, tot in zip(cods, descs, qtys, netos, totals):
            # Consulta el material por código o descripción
            mat = (
                supabase.table("materiales")
                .select("*")
                .eq("material", desc)
                .limit(1)
                .execute()
                .data
            )
            mat = mat[0] if mat else {}

            tipo_val = mat.get("tipo", "")
            item_val = mat.get("item", "")

            precio_unitario = parse_monto(net)
            total_num       = parse_monto(tot)

            rows.append({
                "orden_compra":     orden_compra,
                "fecha":            fecha,
                "mes":              mes,
                "semana":           semana,
                "proveedor":        proveedor_id,
                "tipo_de_entrega":  tipo_de_entrega,
                "metodo_de_pago":   condicion_pago,
                "condicion_de_pago":condicion_pago,
                "fac_sin_iva":      fac_sin_iva,
                "proyecto":         proyecto_id,
                "solicita":         solicitante,
                "art_corr":         corr,
                "codigo":           cod,
                "descripcion":      desc,
                "cantidad":         int(qty),
                "precio_unitario":  precio_unitario,
                "total":            total_num,
                "tipo":             tipo_val,
                "item":             item_val,
                "estado_pago":      "0"
            })
            corr += 1

        if not rows:
            flash("Debes ingresar al menos una línea con cantidad.", "warning")
            return redirect(url_for("ordenes.new_orden"))

        res = supabase.table("orden_de_compra").insert(rows).execute()
        if getattr(res, "error", None):
            flash(f"Error al guardar: {res.error}", "danger")
        else:
            flash(f"Orden de Compra {orden_compra} guardada exitosamente.", "success")

        return redirect(url_for("ordenes.new_orden"))

    # GET: renderizar formulario
    return render_template(
        "ordenes/form_modern.html",
        next_num=next_num,
        tipos_entrega=tipos_entrega,
        plazos_pago=plazos_pago,
        history=history,
        proveedores=proveedores,
        proyectos=proyectos,
        trabajadores=trabajadores
    )


@bp.route("/pdf", methods=["POST"])
@require_modulo('orden_de_compra')
def generate_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=20 * mm, bottomMargin=30 * mm
    )

    supabase = current_app.config['SUPABASE']

    # ——— Recoger datos del formulario ———
    orden_compra     = request.form["next_num"]
    tipo_entrega     = request.form["tipo_entrega"]
    plazo_pago       = request.form["plazo_pago"]
    # Nueva lógica: checkbox "incluir_iva" está marcado por defecto
    # Si está marcado = incluir IVA (sin_iva = False)
    # Si no está marcado = no incluir IVA (sin_iva = True)
    incluir_iva = request.form.get("incluir_iva") is not None
    sin_iva = not incluir_iva  # Invertir la lógica
    observaciones = request.form.get("observaciones", "")
    
    # Debug: Log del valor
    print(f"DEBUG PDF: incluir_iva recibido = {request.form.get('incluir_iva')}")
    print(f"DEBUG PDF: incluir_iva procesado = {incluir_iva}")
    print(f"DEBUG PDF: sin_iva calculado = {sin_iva}")
    print(f"DEBUG PDF: form keys = {list(request.form.keys())}")
    print(f"DEBUG PDF: form values = {dict(request.form)}")

    # --- NUEVO: Obtener nombres y RUT desde Supabase ---
    proveedor_id = request.form.get("proveedor_id")
    proveedor_nombre = ""
    rut = ""
    if proveedor_id:
        proveedor_row = supabase.table("proveedores").select("nombre,rut").eq("id", proveedor_id).execute().data
        if proveedor_row:
            proveedor_nombre = proveedor_row[0]["nombre"]
            rut = proveedor_row[0]["rut"]

    proyecto_id = request.form.get("proyecto_id")
    proyecto = ""
    if proyecto_id:
        proyecto_row = supabase.table("proyectos").select("proyecto").eq("id", proyecto_id).execute().data
        if proyecto_row:
            proyecto = proyecto_row[0]["proyecto"]

    solicitante_id = request.form.get("solicitado_por")
    solicitante = ""
    if solicitante_id:
        trabajador_row = supabase.table("trabajadores").select("nombre").eq("id", solicitante_id).execute().data
        if trabajador_row:
            solicitante = trabajador_row[0]["nombre"]

    cods   = request.form.getlist("cod_linea[]")
    descs  = request.form.getlist("desc_linea[]")
    qtys   = request.form.getlist("cant_linea[]")
    netos  = request.form.getlist("neto_linea[]")
    totals = request.form.getlist("total_linea[]")

    # Construimos la lista de “líneas” para ReportLab
    lineas = [
        [cod, desc, int(qty), parse_monto(net), parse_monto(tot)]
        for cod, desc, qty, net, tot
        in zip(cods, descs, qtys, netos, totals)
        if cod and desc and qty and qty.strip() and float(qty) > 0
    ]

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]

    # Estilo para las condiciones (letra más pequeña)
    cond_style = ParagraphStyle(
        "Condiciones", parent=normal,
        fontSize=6, leading=8, alignment=TA_JUSTIFY
    )
    condiciones = [
        "1. La presente Orden de Compra (OC) podrá ser modificada, ajustada o terminada por Somyl S.A. en cualquier momento, de manera total o parcial, sin alegación de motivo o causa alguna, mediante la notificación escrita física o por correo electrónico al proveedor con una anticipación de 5 (cinco) días.",
        "2. La presente Orden de Compra no obliga a Somyl S.A. a adquirir o comprar la totalidad de esta; el pago efectivo estará definido cuando el proveedor entregue la GUIA DE DESPACHO o DOCUMENTO DE ACEPTACIÓN relacionada a la OC y aceptada por Somyl S.A.",
        "3. Los servicios o material suministrados bajo esta OC tendrán una garantía de 3 Meses o hasta la aceptación total del cliente final de Somyl S.A.",
        "4. El proveedor emitirá su factura después de recibir firmada la GUIA DE DESPACHO o notificación oficial por correo electrónico por parte del área de administración de Somyl S.A. El Subcontratista debe incluir todos los impuestos del gobierno, gravámenes y tasas que correspondan. En caso de no contar con la notificación y proceder a realizar la factura, el proveedor no tiene derecho de reclamo o denuncia de incumplimiento de pago en el plazo que corresponda; este plazo se ajustará una vez Somyl S.A. acepte dicha factura.",
        "5. Toda factura emitida a Somyl S.A. debe ser enviada al Departamento de Administración al correo electrónico indicado en esta OC."
    ]
    cond_para = Paragraph("<br/>".join(condiciones), cond_style)

    # ——— Pie de página: solo líneas, firmas y luego condiciones ———
    def draw_footer(canvas, doc):
        width, height = A4
        cw = width - doc.leftMargin - doc.rightMargin

        # Dibujar línea horizontal para firmas unos 35 mm sobre el borde inferior
        line_y = 35 * mm
        canvas.saveState()
        canvas.setStrokeColor(colors.black)
        canvas.line(doc.leftMargin, line_y, doc.leftMargin + cw, line_y)
        canvas.restoreState()

        # Texto de firmas justo encima de la línea
        canvas.setFont("Helvetica", 10)
        canvas.drawCentredString(doc.leftMargin + cw * 0.25, line_y + 2 * mm, "Luis Medina")
        canvas.drawCentredString(doc.leftMargin + cw * 0.75, line_y + 2 * mm, "Aprobación de Gerencia")

        # Texto de condiciones justo debajo de la línea
        cond_y = line_y - 4 * mm
        cond_para.wrapOn(canvas, cw, height)
        cond_para.drawOn(canvas, doc.leftMargin, cond_y - cond_para.height)

    # ——— Construir el contenido principal del PDF (story) ———
    story = []

    emisora = [
        Paragraph("SOMYL S.A.", h2),
        Paragraph("RUT: 76.002.581-K", normal),
        Paragraph("Giro: TELECOMUNICACIONES", normal),
        Paragraph("PUERTA ORIENTE 361 OF 311 B TORRE B COLINA", normal),
        Paragraph("FONO: 232642974", normal),
    ]
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    hoy = date.today()
    fecha_str = f"{hoy.day} de {meses[hoy.month - 1]} de {hoy.year}"

    header_data = [
        [
            emisora,
            [
                Paragraph("ORDEN DE COMPRA", h1),
                Paragraph(f"N° {orden_compra}", normal),
                Paragraph(f"Fecha: {fecha_str}", normal),
            ]
        ]
    ]
    header_tbl = Table(header_data, colWidths=[100 * mm, 70 * mm])
    header_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.extend([header_tbl, Spacer(1, 6)])

    hr = Table([[""]], colWidths=[170 * mm])
    hr.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.black)]))
    story.extend([hr, Spacer(1, 12)])

    for txt in (
        f"<b>Señores:</b> {proveedor_nombre} (RUT: {rut})",
        f"<b>Tipo de Entrega:</b> {tipo_entrega}",
        f"<b>Plazo de Pago:</b> {plazo_pago}" + (" (Sin IVA)" if sin_iva else ""),
        f"<b>Proyecto:</b> {proyecto}",
        f"<b>Solicitado por:</b> {solicitante}"
    ):
        story.append(Paragraph(txt, normal))
    story.append(Spacer(1, 12))

    # ——— Tabla de líneas ———
    data = [["CÓDIGO", "DESCRIPCIÓN", "CANTIDAD", "NETO", "TOTAL"]]
    for ln in lineas:
        desc_para = Paragraph(str(ln[1]), normal)
        data.append([
            ln[0],
            desc_para,
            ln[2],
            formato_pesos(ln[3]),
            formato_pesos(ln[4])
        ])

    tbl = Table(
        data,
        colWidths=[25 * mm, 80 * mm, 20 * mm, 25 * mm, 25 * mm]  # Ajusta el ancho de descripción
    )
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (2, 1), (4, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),  # Descripción alineada a la izquierda
    ]))
    story.extend([tbl, Spacer(1, 12)])

    # ——— Observaciones (si existen) ———
    if observaciones:
        story.extend([
            Paragraph("<b>Observaciones:</b>", normal),
            Paragraph(observaciones, normal),
            Spacer(1, 12)
        ])

    # ——— Calcular totales ———
    total_neto = sum(ln[4] for ln in lineas)  # Suma los totales de cada línea
    iva = 0 if sin_iva else round(total_neto * 0.19)  # IVA = 0 si es sin IVA
    total_final = total_neto + iva
    
    # Debug: Log del cálculo de IVA
    print(f"DEBUG PDF TOTALES: sin_iva = {sin_iva}")
    print(f"DEBUG PDF TOTALES: total_neto = {total_neto}")
    print(f"DEBUG PDF TOTALES: iva calculado = {iva}")
    print(f"DEBUG PDF TOTALES: total_final = {total_final}")

    # Texto del IVA que cambia según si es exento o no
    iva_text = "IVA (19%) - EXENTO:" if sin_iva else "IVA (19%):"

    totales_tbl = Table([
        ["", "Total Neto:", formato_pesos(total_neto)],
        ["", iva_text, formato_pesos(iva)],
        ["", "Total:", formato_pesos(total_final)],
    ], colWidths=[100*mm, 35*mm, 35*mm])
    totales_tbl.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.extend([totales_tbl, Spacer(1, 12)])

    # ——— Espacio en blanco para que la firma y las condiciones (dibujadas en el pie) quepan ———
    story.append(Spacer(1, 20 * mm))

    # ——— Construir el PDF, con draw_footer en cada página ———
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)

    pdf = buffer.getvalue()
    buffer.close()

    filename = f"O. Compra {orden_compra} {proveedor_nombre}.pdf"
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@bp.route("/api/proveedores")
def api_proveedores():
    supabase = current_app.config['SUPABASE']
    term = request.args.get("term", "")
    if not term:
        return jsonify({"results": []})
    
    # Intentar cache primero
    cached_results = get_select2_cached_results("proveedores", term)
    if cached_results is not None:
        return jsonify({"results": cached_results})
    
    # Consulta optimizada con índices
    proveedores = supabase.table("proveedores") \
        .select("id,nombre,rut") \
        .ilike("nombre", f"%{term}%") \
        .limit(20) \
        .execute().data or []
    
    results = [{
        "id": p["id"],
        "text": p["nombre"],
        "rut": p["rut"]
    } for p in proveedores]
    
    # Cachear resultados
    if results:
        cache_select2_results("proveedores", term, results)
    
    return jsonify({"results": results})


@bp.route("/api/proyectos")
def api_proyectos():
    supabase = current_app.config['SUPABASE']
    term = request.args.get("term", "")
    if not term:
        return jsonify({"results": []})
    
    # Intentar cache primero
    cached_results = get_select2_cached_results("proyectos", term)
    if cached_results is not None:
        return jsonify({"results": cached_results})
    
    # Optimizado: usar índice GIN y consulta SQL directa
    proyectos = supabase.table("proyectos") \
        .select("id,proyecto") \
        .ilike("proyecto", f"%{term}%") \
        .limit(20) \
        .execute().data or []
    
    results = [{
        "id": p["id"],
        "text": p["proyecto"]
    } for p in proyectos]
    
    # Cachear resultados
    if results:
        cache_select2_results("proyectos", term, results)
    
    return jsonify({"results": results})


@bp.route("/api/plazos_pago")
def api_plazos_pago():
    supabase = current_app.config['SUPABASE']
    term = request.args.get("term", "")
    if not term:
        return jsonify({"results": []})
    
    # Optimizado: usar índice y consulta SQL directa
    plazos = supabase.table("plazos_pago") \
        .select("id,plazo") \
        .ilike("plazo", f"%{term}%") \
        .limit(20) \
        .execute().data or []
    
    results = [{"id": p["id"], "text": p["plazo"]} for p in plazos]
    return jsonify({"results": results})


@bp.route("/api/tipos_entrega")
def api_tipos_entrega():
    supabase = current_app.config['SUPABASE']
    term = request.args.get("term", "")
    if not term:
        return jsonify({"results": []})
    
    # Optimizado: usar índice y consulta SQL directa
    tipos = supabase.table("tipos_entrega") \
        .select("id,tipo") \
        .ilike("tipo", f"%{term}%") \
        .limit(20) \
        .execute().data or []
    
    results = [{"id": t["id"], "text": t["tipo"]} for t in tipos]
    return jsonify({"results": results})


@bp.route("/api/trabajadores")
def api_trabajadores():
    supabase = current_app.config['SUPABASE']
    term = request.args.get("term", "")
    if not term:
        return jsonify({"results": []})
    
    # Intentar cache primero
    cached_results = get_select2_cached_results("trabajadores", term)
    if cached_results is not None:
        return jsonify({"results": cached_results})
    
    # Optimizado: usar índice GIN y consulta SQL directa
    trabajadores = supabase.table("trabajadores") \
        .select("id,nombre") \
        .ilike("nombre", f"%{term}%") \
        .limit(20) \
        .execute().data or []
    
    results = [{"id": t["id"], "text": t["nombre"]} for t in trabajadores]
    
    # Cachear resultados
    if results:
        cache_select2_results("trabajadores", term, results)
    
    return jsonify({"results": results})


@bp.route("/api/materiales")
def api_materiales():
    supabase = current_app.config['SUPABASE']
    term = request.args.get("term", "")
    if not term or len(term) < 2:  # Mínimo 2 caracteres para buscar
        return jsonify({"results": []})

    # Intentar obtener del cache primero
    cached_results = get_cached_materiales(term)
    if cached_results:
        return jsonify({"results": cached_results})

    try:
        # Búsqueda optimizada: buscar en material O código en una sola consulta
        materiales = supabase.table("materiales") \
            .select("cod,material,tipo,item") \
            .or_(f"material.ilike.%{term}%,cod.ilike.%{term}%") \
            .limit(15) \
            .execute().data or []

        if not materiales:
            return jsonify({"results": []})

        # Estrategia optimizada para precios: solo para materiales más relevantes
        material_names = [m["material"] for m in materiales[:10]]  # Solo top 10
        
        # Obtener precios de manera más eficiente
        precios_data = {}
        
        if material_names:
            # Intentar una consulta batch optimizada
            try:
                # Crear un query más eficiente agrupando por material
                for material_name in material_names:
                    # Consulta optimizada con índices
                    history = supabase.table("orden_de_compra") \
                        .select("precio_unitario") \
                        .eq("descripcion", material_name) \
                        .not_.is_("precio_unitario", "null") \
                        .order("fecha", desc=True) \
                        .limit(1) \
                        .execute().data
                    
                    if history and len(history) > 0 and history[0].get("precio_unitario"):
                        try:
                            precio = float(history[0]["precio_unitario"])
                            precios_data[material_name] = precio if precio > 0 else 0
                        except (ValueError, TypeError):
                            precios_data[material_name] = 0
                    else:
                        precios_data[material_name] = 0
                        
            except Exception as e:
                # Si hay error en consulta de precios, continuar sin precios
                current_app.logger.warning(f"Error obteniendo precios: {e}")
                precios_data = {name: 0 for name in material_names}

        # Construir resultados optimizados
        results = []
        for i, m in enumerate(materiales):
            # Solo buscar precio para los primeros 10 (optimización)
            ultimo_precio = precios_data.get(m["material"], 0) if i < 10 else 0
            
            results.append({
                "id": m["material"],
                "text": m["material"],
                "codigo": m["cod"],
                "ultimo_precio": ultimo_precio,
                "tipo": m.get("tipo", ""),
                "item": m.get("item", "")
            })

        # Guardar en cache solo si la búsqueda fue exitosa
        if results:
            set_cached_materiales(term, results)
        
        return jsonify({"results": results})
        
    except Exception as e:
        current_app.logger.error(f"Error en api_materiales: {e}")
        return jsonify({"results": [], "error": "Error interno del servidor"}), 500