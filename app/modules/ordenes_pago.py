from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    jsonify
)
from datetime import date
from flask_mail import Message
import pdfkit
from flask import render_template
import logging
from app.modules.usuarios import require_modulo  # <-- Agrega esta línea

bp = Blueprint(
    "ordenes_pago", __name__,
    template_folder="../templates/ordenes_pago"
)

@bp.route("/", methods=["GET"])
@require_modulo('orden_de_pago')
def list_ordenes_pago():
    supabase = current_app.config["SUPABASE"]

    # Próximo número de orden de pago
    last = (
        supabase
        .table("orden_de_pago")
        .select("orden_numero")
        .order("orden_numero", desc=True)
        .limit(1)
        .execute()
        .data
    ) or []
    next_num = (last[0]["orden_numero"] + 1) if last else 1

    # Traer todas las OP (para estado_documento & ingreso_id)
    pagos_all = (
        supabase
        .table("orden_de_pago")
        .select("id, ingreso_id, orden_numero, proveedor_nombre, fecha, factura, estado_documento")
        .order("orden_numero")
        .execute()
        .data
    ) or []

    # Agrupar por orden_numero y quedarnos sólo con el primero de cada OP
    pagos_unicos = {}
    for p in pagos_all:
        num = p["orden_numero"]
        if num not in pagos_unicos:
            pagos_unicos[num] = p

    # Sólo pendientes de documento
    pagos = [p for p in pagos_unicos.values() if p["estado_documento"] == "pendiente"]

    # DataLists: proveedores y trabajadores
    providers = (
        supabase
        .table("proveedores")
        .select("id, nombre")
        .execute()
        .data
    ) or []
    trabajadores = (
        supabase
        .table("trabajadores")
        .select("id, nombre, correo")
        .execute()
        .data
    ) or []

    # AJAX detail=1: listar líneas de ingresos no pagadas por guía+OC
    if request.args.get("detail"):
        guia = request.args.get("guia")
        oc = request.args.get("oc", type=int)

        ingresos = (
            supabase
            .table("ingresos")
            .select("id, orden_compra, guia_recepcion, art_corr, recepcion, neto_unitario, material")
            .eq("guia_recepcion", guia)
            .eq("orden_compra", oc)
            .execute()
            .data
        ) or []

        # map id→material name
        mat_ids = {i["material"] for i in ingresos}
        mats = (
            supabase
            .table("materiales")
            .select("id, material")
            .in_("id", list(mat_ids))
            .execute()
            .data
        ) or []
        mat_map = {m["id"]: m["material"] for m in mats}

        # ingresos ya usados en OP
        pagados_ids = {p["ingreso_id"] for p in pagos_all if p.get("ingreso_id")}

        result = []
        for i in ingresos:
            if i["id"] in pagados_ids:
                continue
            result.append({
                "ingreso_id":    i["id"],
                "descripcion":   mat_map.get(i["material"], ""),
                "recepcion":     int(i.get("recepcion") or 0),
                "neto_unitario": float(i.get("neto_unitario") or 0),
                "art_corr":      i.get("art_corr"),
                "orden_compra":  i.get("orden_compra"),
                "material_id":   i.get("material")
            })
        return jsonify(result)

    # GET normal: si se filtró proveedor, armar docs pendientes
    nombre_proveedor = request.args.get("nombre_proveedor", type=str)
    provider_id = None
    docs = []

    if nombre_proveedor:
        prov = (
            supabase
            .table("proveedores")
            .select("id")
            .eq("nombre", nombre_proveedor)
            .limit(1)
            .execute()
            .data
        ) or []
        if prov:
            provider_id = prov[0]["id"]
            ingresos = (
                supabase
                .table("ingresos")
                .select("id, orden_compra, guia_recepcion, art_corr, neto_recepcion")
                .eq("proveedor", provider_id)
                .execute()
                .data
            ) or []

            pagados_ids = {p["ingreso_id"] for p in pagos_all if p.get("ingreso_id")}
            pendientes = [i for i in ingresos if i["id"] not in pagados_ids]

            grupos = {}
            for i in pendientes:
                key = (i["guia_recepcion"], i["orden_compra"])
                if key not in grupos:
                    grupos[key] = {
                        "guia_recepcion":       i["guia_recepcion"],
                        "orden_compra":         i["orden_compra"],
                        "total_neto_recepcion": 0.0
                    }
                grupos[key]["total_neto_recepcion"] += float(i.get("neto_recepcion") or 0)
            docs = list(grupos.values())

    return render_template(
        "ordenes_pago/form.html",
        pagos=pagos,
        providers=providers,
        trabajadores=trabajadores,
        docs=docs,
        next_num=next_num,
        nombre_proveedor=nombre_proveedor or "",
        provider_id=provider_id or ""
    )


@bp.route("/new_orden_pago", methods=["POST"])
@require_modulo('orden_de_pago')
def new_orden_pago():
    print("=== new_orden_pago start ===")
    current_app.logger.info("new_orden_pago(): inicio de la función")
    supabase = current_app.config["SUPABASE"]
    f = request.form

    orden_numero      = int(f.get("next_num", 0))
    provider_id       = int(f.get("proveedor_id", 0))
    proveedor_nombre  = f.get("nombre_proveedor", "")
    autoriza_id       = f.get("autoriza_id") or None
    fecha_factura     = f.get("fecha_factura")
    vencimiento       = f.get("vencimiento")
    estado_pago       = f.get("estado_pago")
    detalle_compra    = f.get("detalle_compra", "")

    # Listas de inputs múltiples
    ingreso_ids        = f.getlist("ingreso_id[]")
    orden_compras      = f.getlist("orden_compra[]")
    guia_recepciones   = f.getlist("guia_recepcion[]")
    art_corrs          = f.getlist("art_corr[]")
    material_ids       = f.getlist("material[]")
    descs              = f.getlist("descripcion[]")
    recepciones        = f.getlist("recepcion[]")
    neto_unitarios     = f.getlist("neto_unitario[]")
    # facturas           = f.getlist("factura[]")

    # Por cada línea seleccionada, insertamos una fila
    for i, ingreso_id in enumerate(ingreso_ids):
        orden_compra_int   = int(orden_compras[i])
        doc_recep          = guia_recepciones[i]
        art_corr_int       = int(art_corrs[i])

        # Buscar el ID padre de orden_de_compra por orden_compra y art_corr
        oc_res = supabase.table("orden_de_compra") \
            .select("id, proyecto, condicion_de_pago") \
            .eq("orden_compra", orden_compra_int) \
            .eq("art_corr", art_corr_int) \
            .single() \
            .execute()

        if getattr(oc_res, "error", None) or not oc_res.data:
            current_app.logger.debug(f"OC línea no encontrada: orden_compra={orden_compra_int}, art_corr={art_corr_int}, respuesta={oc_res}")
            flash(f"Línea OC {orden_compra_int} - art_corr {art_corr_int} no existe en orden_de_compra.", "danger")
            continue

        orden_de_compra_id = oc_res.data["id"]
        proyecto_val       = oc_res.data.get("proyecto")
        condicion_pago_val = oc_res.data.get("condicion_de_pago")

        # Obtener tipo e item desde tabla materiales
        mat_res = supabase.table("materiales") \
            .select("tipo, item") \
            .eq("id", int(material_ids[i])) \
            .single() \
            .execute()
        tipo_val = mat_res.data.get("tipo")
        item_val = mat_res.data.get("item")

        # Asignar documento y estado según doc_recep
        factura_val = doc_recep or ""
        estado_doc  = "completado" if doc_recep else "pendiente"

        material_id_int    = int(material_ids[i])
        descripcion        = descs[i]
        cantidad_int       = int(recepciones[i])
        unitario_float     = float(neto_unitarios[i])
        neto_total         = cantidad_int * unitario_float
        costo_final_con_iva= neto_total * 1.19

        supabase.table("orden_de_pago").insert({
            "ingreso_id":           int(ingreso_id),
            "orden_compra":         orden_de_compra_id,
            "doc_recep":            doc_recep,
            "art_corr":             art_corr_int,
            "material":             material_id_int,
            "material_nombre":      descripcion,
            "cantidad":             cantidad_int,
            "neto_unitario":        unitario_float,
            "neto_total_recibido":  neto_total,
            "costo_final_con_iva":  costo_final_con_iva,
            "orden_numero":         orden_numero,
            "proveedor":            provider_id,
            "proveedor_nombre":     proveedor_nombre,
            "autoriza":            f.get("autoriza_input"),
            "autoriza_nombre":     f.get("autoriza_input"),
            "fecha_factura":        fecha_factura,
            "vencimiento":          vencimiento,
            "estado_pago":          estado_pago,
            "detalle_compra":       detalle_compra,
            "proyecto":            proyecto_val,
            "condicion_pago":      condicion_pago_val,
            "factura":             factura_val,
            "estado_documento":    estado_doc,
            "tipo":                tipo_val,
            "item":                item_val,
            "fecha":                date.today().isoformat()
        }).execute()

    print("=== before PDF generation ===")
    # — Generar PDF en memoria para adjuntar —
    pdf_context = {
        'empresa': {
            'nombre': 'Somyl S.A.',
            'rut': '76.002.581-K',
            'rubro': 'TELECOMUNICACIONES',
            'direccion': 'PUERTA ORIENTE 361 OF 311 B TORRE B COLINA',
            'telefono': '232642974'
        },
        'proveedor': {
            'paguese_a': proveedor_nombre,
            'nombre':    proveedor_nombre,
            'rut':        '',
            'cuenta':     '',
            'banco':      '',
            'correo':     ''
        },
        'numero':         orden_numero,
        'facturas':       guia_recepciones,
        'ocs':            orden_compras,
        'cond_pago':      estado_pago,
        'fecha_factura':  fecha_factura,
        'fecha_venc':     vencimiento,
        'detalle_op':     detalle_compra,
        'detalle_material': [
            {
                'guia':        guia_recepciones[j],
                'oc':          orden_compras[j],
                'descripcion': descs[j]
            } for j in range(len(ingreso_ids))
        ],
        'total_neto':     float(request.form.get('total_neto', 0)),
        'total_iva':      float(request.form.get('total_iva', 0)),
        'total_pagar':    float(request.form.get('total_pagar', 0)),
        'autorizador': {
            'nombre': f.get('autoriza_input', ''),
            'correo': f.get('autoriza_email', '')
        },
        'fecha_emision':  date.today().isoformat()
    }
    html = render_template('ordenes_pago/pdf_template.html', **pdf_context)
    config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf')
    options = {'enable-local-file-access': None}
    pdf_bytes = pdfkit.from_string(html, False, configuration=config, options=options)

    # — Construir y enviar correo —
    # mail = current_app.extensions['mail']
    # msg = Message(
    #     subject=f"orden de pago {proveedor_nombre}",
    #     recipients=["carlosalegria@me.com"]
    # )
    # msg.body = (
    #     f"Buenas tardes.\n\n"
    #     f"Junto con saludar, orden de pago N{orden_numero} de {proveedor_nombre}.\n\n"
    #     f"Saludos cordiales."
    # )
    # # adjuntar PDF
    # msg.attach(
    #     filename=f"orden_pago_{orden_numero}_{proveedor_nombre}.PDF",
    #     content_type="application/pdf",
    #     data=pdf_bytes
    # )
    # # adjuntar archivos si existen
    # for field in ('documento1', 'documento2'):
    #     file = request.files.get(field)
    #     if file and file.filename:
    #         msg.attach(
    #             filename=file.filename,
    #             content_type=file.content_type,
    #             data=file.read()
    #         )
    # print("=== before mail.send ===")
    # try:
    #     mail.send(msg)
    #     print("=== mail.send completed ===")
    #     current_app.logger.info("Correo enviado correctamente")
    # except Exception as e:
    #     current_app.logger.error("Error al enviar correo: %s", e, exc_info=True)

    flash(f"Orden de Pago Nº{orden_numero} creada exitosamente.", "success")
    return redirect(url_for("ordenes_pago.list_ordenes_pago"))


@bp.route("/complete_doc/<int:id>", methods=["POST"])
def complete_doc(id):
    supabase = current_app.config["SUPABASE"]
    data = request.get_json() or {}
    factura = data.get("factura", "").strip()
    if factura:
        supabase.table("orden_de_pago")\
            .update({"factura": factura, "estado_documento": "completado"})\
            .eq("id", id).execute()
        return jsonify(success=True)
    return jsonify(success=False)


@bp.route("/guardar_docs", methods=["POST"])
def guardar_docs():
    supabase = current_app.config["SUPABASE"]
    data = request.get_json() or {}
    documentos = data.get("documentos", [])

    if not documentos:
        return jsonify(success=False, message="No se recibieron documentos para guardar"), 400

    actualizados = 0
    for doc in documentos:
        try:
            op_id   = int(doc.get("op_id"))
            factura = doc.get("numeroDocumento", "").strip()
        except (TypeError, ValueError):
            continue

        if not factura:
            continue

        supabase.table("orden_de_pago") \
            .update({"factura": factura, "estado_documento": "completado"}) \
            .eq("id", op_id) \
            .execute()
        actualizados += 1

    if actualizados:
        return jsonify(
            success=True,
            message=f"{actualizados} documento(s) guardado(s) con éxito"
        )
    else:
        return jsonify(
            success=False,
            message="No se guardó ningún documento"
        ), 200


@bp.route("/api/proveedores")
def api_proveedores():
    supabase = current_app.config["SUPABASE"]
    term = request.args.get("term", "")
    if not term:
        return jsonify({"results": []})
    proveedores = (
        supabase
        .table("proveedores")
        .select("id, nombre")
        .ilike("nombre", f"%{term}%")
        .limit(20)
        .execute()
        .data
    ) or []
    results = [{"id": p["id"], "text": p["nombre"]} for p in proveedores]
    return jsonify({"results": results})

@bp.route("/api/trabajadores")
def api_trabajadores():
    supabase = current_app.config["SUPABASE"]
    term = request.args.get("term", "")
    if not term:
        return jsonify({"results": []})
    trabajadores = (
        supabase
        .table("trabajadores")
        .select("id, nombre, correo")
        .ilike("nombre", f"%{term}%")
        .limit(20)
        .execute()
        .data
    ) or []
    results = [{"id": t["id"], "text": t["nombre"], "correo": t["correo"]} for t in trabajadores]
    return jsonify({"results": results})