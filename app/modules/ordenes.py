# app/modules/ordenes.py

import io
import re
from datetime import date
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

bp = Blueprint("ordenes", __name__, template_folder="../templates/ordenes")


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
    providers    = supabase.table("proveedores").select("id,nombre,rut").execute().data or []
    proyectos    = supabase.table("proyectos").select("id,proyecto").execute().data or []
    trabajadores = supabase.table("trabajadores").select("nombre").execute().data or []
    materiales   = supabase.table("materiales").select("cod,material,tipo,item").execute().data or []
    tipos_entrega = ["30 DIAS","45 DIAS","60 DIAS","90 DIAS","INMEDIATA","OTRO"]
    plazos_pago   = ["CONTADO","30 DIAS","45 DIAS","60 DIAS","90 DIAS","OTRO"]
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
        fac_sin_iva     = 1 if request.form.get("sin_iva") else 0
        proyecto_id     = int(request.form["proyecto_id"])
        solicitante     = request.form["solicitado_por"]

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
        for i, qty in enumerate(qtys):
            if not qty or float(qty) <= 0 or not descs[i]:
                continue

            mat = next((m for m in materiales if m["material"] == descs[i]), {})
            tipo_val = mat.get("tipo", "")
            item_val = mat.get("item", "")

            precio_unitario = parse_monto(netos[i])
            total_num       = parse_monto(totals[i])

            rows.append({
                "orden_compra":     orden_compra,       # as integer
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
                "codigo":           cods[i],
                "descripcion":      descs[i],
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
        "ordenes/form.html",
        next_num=next_num,
        providers=providers,
        proyectos=proyectos,
        trabajadores=trabajadores,
        materiales=materiales,
        tipos_entrega=tipos_entrega,
        plazos_pago=plazos_pago,
        history=history
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
    sin_iva          = request.form.get("sin_iva") is not None
    observaciones    = request.form.get("observaciones", "")

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
    iva = round(total_neto * 0.19)
    total_final = total_neto + iva

    totales_tbl = Table([
        ["", "Total Neto:", formato_pesos(total_neto)],
        ["", "IVA (19%):", formato_pesos(iva)],
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
    proveedores = supabase.table("proveedores").select("id,nombre,rut").execute().data or []
    results = []
    for p in proveedores:
        if term.lower() in p["nombre"].lower():
            results.append({
                "id": p["id"],
                "text": p["nombre"],
                "rut": p["rut"]
            })
    return jsonify({"results": results})


@bp.route("/api/proyectos")
def api_proyectos():
    supabase = current_app.config['SUPABASE']
    term = request.args.get("term", "")
    proyectos = supabase.table("proyectos").select("id,proyecto").execute().data or []
    results = []
    for p in proyectos:
        if term.lower() in p["proyecto"].lower():
            results.append({
                "id": p["id"],
                "text": p["proyecto"]
            })
    return jsonify({"results": results})


@bp.route("/api/plazos_pago")
def api_plazos_pago():
    supabase = current_app.config['SUPABASE']
    term = request.args.get("term", "")
    plazos = supabase.table("plazos_pago").select("id,plazo").execute().data or []
    results = []
    for p in plazos:
        if term.lower() in p["plazo"].lower():
            results.append({"id": p["id"], "text": p["plazo"]})
    return jsonify({"results": results})


@bp.route("/api/tipos_entrega")
def api_tipos_entrega():
    supabase = current_app.config['SUPABASE']
    term = request.args.get("term", "")
    tipos = supabase.table("tipos_entrega").select("id,tipo").execute().data or []
    results = []
    for t in tipos:
        if term.lower() in t["tipo"].lower():
            results.append({"id": t["id"], "text": t["tipo"]})
    return jsonify({"results": results})


@bp.route("/api/trabajadores")
def api_trabajadores():
    supabase = current_app.config['SUPABASE']
    term = request.args.get("term", "")
    trabajadores = supabase.table("trabajadores").select("id,nombre").execute().data or []
    results = []
    for t in trabajadores:
        if term.lower() in t["nombre"].lower():
            results.append({"id": t["id"], "text": t["nombre"]})
    return jsonify({"results": results})


@bp.route("/api/materiales")
def api_materiales():
    supabase = current_app.config['SUPABASE']
    term = request.args.get("term", "")
    materiales = supabase.table("materiales").select("cod,material,tipo,item").execute().data or []
    results = []
    for m in materiales:
        if term.lower() in m["material"].lower() or term.lower() in m["cod"].lower():
            # Buscar el último precio en orden_de_compra por descripción exacta
            history = supabase.table("orden_de_compra") \
                .select("precio_unitario,descripcion") \
                .eq("descripcion", m["material"]) \
                .order("orden_compra", desc=True) \
                .limit(1) \
                .execute().data
            ultimo_precio = 0
            if history and history[0].get("precio_unitario"):
                try:
                    ultimo_precio = float(history[0]["precio_unitario"])
                except Exception:
                    ultimo_precio = 0

            results.append({
                "id": m["material"],      # <-- ahora el value será la descripción
                "text": m["material"],    # <-- lo que se muestra
                "codigo": m["cod"],       # <-- código aparte
                "ultimo_precio": ultimo_precio,
                "tipo": m["tipo"],
                "item": m["item"]
            })
    return jsonify({"results": results})