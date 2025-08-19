from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    jsonify,
    request as flask_request
)
from datetime import date
from flask_mail import Message
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False
    current_app.logger.warning("pdfkit no disponible - PDFs deshabilitados")
from flask import render_template
import logging
from app.modules.usuarios import require_modulo
from app.utils.cache import get_select2_cached_results, cache_select2_results
from flask_login import current_user
from utils.logger import registrar_log_actividad

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

    # --- Paginación automática para grandes volúmenes ---
    def fetch_all_rows(table, select_str, order_col=None, desc=False):
        page_size = 1000
        offset = 0
        all_rows = []
        while True:
            q = supabase.table(table).select(select_str)
            if order_col:
                q = q.order(order_col, desc=desc)
            q = q.range(offset, offset + page_size - 1)
            batch = q.execute().data or []
            all_rows.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        return all_rows

    # LÓGICA ORIGINAL RESTAURADA: traer todas, agrupar, luego filtrar pendientes
    pagos_all = fetch_all_rows("orden_de_pago", "id, ingreso_id, orden_numero, proveedor_nombre, fecha, factura, estado_documento", "orden_numero")
    
    # Agrupar por orden_numero y quedarnos sólo con el primero de cada OP
    pagos_unicos = {}
    for p in pagos_all:
        num = p["orden_numero"]
        if num not in pagos_unicos:
            pagos_unicos[num] = p
    
    # Sólo pendientes de documento
    pagos = [p for p in pagos_unicos.values() if p["estado_documento"] == "pendiente"]
    
    providers = fetch_all_rows("proveedores", "id, nombre")
    trabajadores = fetch_all_rows("trabajadores", "id, nombre, correo")

    # AJAX detail=1: listar líneas de ingresos no pagadas por guía+OC
    if request.args.get("detail"):
        guia = request.args.get("guia")
        oc = request.args.get("oc", type=int)
        
        # Logging para debug
        current_app.logger.info(f"AJAX detail request: guia={guia}, oc={oc}")
        
        # Construir consulta base
        query = supabase.table("ingresos").select("id, orden_compra, factura, guia_recepcion, art_corr, recepcion, neto_unitario, material")
        
        # Filtrar por orden_compra (siempre debe existir)
        if oc is not None:
            query = query.eq("orden_compra", oc)
        else:
            current_app.logger.warning("Orden de compra no válida o faltante")
            return jsonify([])
        
        # Filtrar por factura (documento principal)
        if guia and guia.upper() not in ["NONE", "SIN_DOCUMENTO", "NULL", ""]:
            query = query.eq("factura", guia)
            current_app.logger.info(f"Buscando ingresos con factura: {guia}")
        else:
            # Si guia es None, "SIN_DOCUMENTO" o vacío, buscar registros con factura nula o vacía
            query = query.or_("factura.is.null,factura.eq.")
            current_app.logger.info(f"Buscando ingresos sin documento/factura (guia={guia})")
        
        ingresos = query.execute().data or []
        current_app.logger.info(f"Ingresos encontrados: {len(ingresos)}")

        # map id→material name
        mat_ids = {i["material"] for i in ingresos if i.get("material")}
        if mat_ids:
            mats = (
                supabase
                .table("materiales")
                .select("id, material")
                .in_("id", list(mat_ids))
                .execute()
                .data
            ) or []
            mat_map = {m["id"]: m["material"] for m in mats}
        else:
            mat_map = {}
        
        current_app.logger.info(f"Materiales encontrados: {len(mat_map)}")

        # ingresos ya usados en OP - LÓGICA ORIGINAL RESTAURADA
        pagados_ids = {p["ingreso_id"] for p in pagos_all if p.get("ingreso_id")}
        current_app.logger.info(f"Ingresos ya pagados: {len(pagados_ids)}")

        result = []
        for i in ingresos:
            if i["id"] in pagados_ids:
                current_app.logger.debug(f"Ingreso {i['id']} ya está pagado, omitiendo")
                continue
                
            material_name = mat_map.get(i["material"], f"Material ID: {i['material']}")
            
            result.append({
                "ingreso_id":    i["id"],
                "descripcion":   material_name,
                "recepcion":     int(i.get("recepcion") or 0),
                "neto_unitario": float(i.get("neto_unitario") or 0),
                "art_corr":      i.get("art_corr"),
                "orden_compra":  i.get("orden_compra"),
                "material_id":   i.get("material")
            })
            
        current_app.logger.info(f"Resultado final: {len(result)} líneas disponibles")
        return jsonify(result)

    # GET normal: si se filtró proveedor, armar docs pendientes
    nombre_proveedor = request.args.get("nombre_proveedor", type=str)
    provider_id = None
    docs = []

    if nombre_proveedor:
        # Verificar si nombre_proveedor es un ID numérico o un nombre
        try:
            # Si es un número, buscar por ID
            provider_id = int(nombre_proveedor)
            prov = (
                supabase
                .table("proveedores")
                .select("id, nombre")
                .eq("id", provider_id)
                .limit(1)
                .execute()
                .data
            ) or []
            if prov:
                nombre_proveedor = prov[0]["nombre"]  # Actualizar con el nombre real
                provider_id = prov[0]["id"]
        except (ValueError, TypeError):
            # Si no es un número, buscar por nombre
            prov = (
                supabase
                .table("proveedores")
                .select("id, nombre")
                .eq("nombre", nombre_proveedor)
                .limit(1)
                .execute()
                .data
            ) or []
            if prov:
                provider_id = prov[0]["id"]
        
        # Si encontramos el proveedor, buscar ingresos
        if provider_id:
            ingresos = (
                supabase
                .table("ingresos")
                .select("id, orden_compra, factura, guia_recepcion, art_corr, neto_recepcion")
                .eq("proveedor", provider_id)
                .execute()
                .data
            ) or []

            # ingresos ya usados en OP - LÓGICA ORIGINAL RESTAURADA
            pagados_ids = {p["ingreso_id"] for p in pagos_all if p.get("ingreso_id")}
            pendientes = [i for i in ingresos if i["id"] not in pagados_ids]

            grupos = {}
            for i in pendientes:
                # Manejar factura nula - usar "SIN_DOCUMENTO" en lugar de "None"
                factura_key = i["factura"] if i["factura"] is not None else "SIN_DOCUMENTO"
                key = (factura_key, i["orden_compra"])
                if key not in grupos:
                    grupos[key] = {
                        "guia_recepcion":       factura_key,  # Mantenemos el nombre por compatibilidad con template
                        "orden_compra":         i["orden_compra"],
                        "total_neto_recepcion": 0.0
                    }
                grupos[key]["total_neto_recepcion"] += float(i.get("neto_recepcion") or 0)
            docs = list(grupos.values())
            # Ordenar docs por 'orden_compra' de mayor a menor
            docs.sort(key=lambda d: d.get('orden_compra', 0), reverse=True)
            
            # Logging para debug
            current_app.logger.info(f"Proveedor encontrado: ID={provider_id}, Nombre={nombre_proveedor}")
            current_app.logger.info(f"Documentos pendientes generados: {len(docs)}")
            for doc in docs:
                current_app.logger.debug(f"Doc: {doc['guia_recepcion']}, OC: {doc['orden_compra']}, Total: {doc['total_neto_recepcion']}")
        else:
            current_app.logger.warning(f"Proveedor no encontrado: {nombre_proveedor}")
    else:
        current_app.logger.info("No se proporcionó nombre_proveedor en la consulta")

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
    
    try:
        supabase = current_app.config["SUPABASE"]
        f = request.form

        orden_numero      = int(f.get("next_num", 0))
        provider_id       = int(f.get("proveedor_id", 0))
        proveedor_nombre  = f.get("nombre_proveedor", "")
        autoriza_id       = f.get("autoriza_id") or None
        fecha_factura     = f.get("fecha_factura")
        vencimiento       = f.get("vencimiento")
        estado_pago       = f.get("estado_pago")
        detalle_compra    = f.get("detalle_compra", "").strip()

        current_app.logger.info(f"Procesando orden {orden_numero} para proveedor {proveedor_nombre}")

        # Validar que el detalle de compra no esté vacío
        if not detalle_compra:
            flash("El campo 'Detalle de Compra' es obligatorio. Debe ingresar al menos un comentario.", "danger")
            return redirect(url_for("ordenes_pago.list_ordenes_pago"))

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
                .select("id, proyecto, condicion_de_pago, fac_sin_iva") \
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
            fac_sin_iva        = oc_res.data.get("fac_sin_iva", 0)  # 0 = con IVA, 1 = sin IVA

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
            # Calcular IVA solo si la orden de compra original no era sin IVA
            costo_final_con_iva= neto_total * (1.0 if fac_sin_iva else 1.19)

            try:
                fecha_actual = date.today().isoformat()
                anio = date.today().year
                payload = {
                    "ingreso_id":           int(ingreso_id),
                    "orden_compra":         orden_compra_int,  # Guardar número de OC, no el ID
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
                    # "fac_sin_iva":         fac_sin_iva,  # Comentado hasta agregar la columna
                    "item":                item_val,
                    "fecha":                fecha_actual,
                    "anio":                 anio
                }
                result = supabase.table("orden_de_pago").insert(payload).execute()
                if hasattr(result, 'error') and result.error:
                    current_app.logger.error(f"Error en inserción Supabase: {result.error}")
                    flash(f"Error al insertar línea {i+1}: {result.error}", "danger")
                    continue
                # Log de actividad
                op_id = result.data[0]["id"] if result.data and isinstance(result.data, list) else None
                registrar_log_actividad(
                    accion="crear",
                    tabla_afectada="orden_de_pago",
                    registro_id=op_id,
                    descripcion=f"Orden de pago creada (línea {i+1}) para proveedor {proveedor_nombre}.",
                    datos_antes=None,
                    datos_despues=payload
                )
                current_app.logger.info(f"Línea {i+1} insertada exitosamente")
            except Exception as e:
                current_app.logger.error(f"Error insertando línea {i+1}: {e}")
                flash(f"Error al insertar línea {i+1}: {str(e)}", "danger")
                continue

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
        
        print("=== before PDF generation ===")
        # Configuración robusta de wkhtmltopdf para producción
        try:
            # Verificar si pdfkit está disponible
            if not PDFKIT_AVAILABLE:
                current_app.logger.warning("pdfkit no disponible - Saltando generación de PDF")
                pdf_bytes = None
            else:
                html = render_template('ordenes_pago/pdf_template.html', **pdf_context)
                config = None
                
                # 1. Intentar con la instalación del sistema (Railway, Heroku, etc.)
                try:
                    import subprocess
                    result = subprocess.run(['which', 'wkhtmltopdf'], capture_output=True, text=True)
                    if result.returncode == 0:
                        wkhtmltopdf_path = result.stdout.strip()
                        current_app.logger.info(f"wkhtmltopdf encontrado en: {wkhtmltopdf_path}")
                        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
                except Exception as e:
                    current_app.logger.warning(f"Error buscando wkhtmltopdf: {e}")
                
                # 2. Fallback a rutas comunes si no se encuentra
                if not config:
                    common_paths = [
                        '/usr/bin/wkhtmltopdf',
                        '/usr/local/bin/wkhtmltopdf',
                        '/bin/wkhtmltopdf',
                        'wkhtmltopdf'  # Usar PATH del sistema
                    ]
                    
                    for path in common_paths:
                        try:
                            config = pdfkit.configuration(wkhtmltopdf=path)
                            # Probar si la configuración funciona
                            test_options = {'enable-local-file-access': None}
                            pdfkit.from_string('<html><body>Test</body></html>', False, configuration=config, options=test_options)
                            current_app.logger.info(f"wkhtmltopdf configurado exitosamente en: {path}")
                            break
                        except Exception as e:
                            current_app.logger.warning(f"Ruta {path} no funciona: {e}")
                            continue
                
                # 3. Si no se encuentra wkhtmltopdf, usar configuración sin path
                if not config:
                    current_app.logger.info("Usando configuración por defecto de wkhtmltopdf")
                    config = None
                
                # Generar PDF con la configuración encontrada
                options = {
                    'enable-local-file-access': None,
                    'page-size': 'A4',
                    'margin-top': '0.75in',
                    'margin-right': '0.75in',
                    'margin-bottom': '0.75in',
                    'margin-left': '0.75in',
                    'encoding': "UTF-8",
                    'no-outline': None
                }
                
                if config:
                    pdf_bytes = pdfkit.from_string(html, False, configuration=config, options=options)
                else:
                    pdf_bytes = pdfkit.from_string(html, False, options=options)
                    
                current_app.logger.info(f"PDF generado exitosamente para orden {orden_numero}")
            
        except Exception as e:
            current_app.logger.error(f"Error generando PDF en new_orden_pago: {e}")
            # En caso de error, continuar sin PDF pero completar el guardado
            pdf_bytes = None
            current_app.logger.warning("Continuando sin PDF debido a error en generación")

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
    # # adjuntar PDF solo si se generó correctamente
    # if pdf_bytes:
    #     msg.attach(
    #         filename=f"orden_pago_{orden_numero}_{proveedor_nombre}.PDF",
    #         content_type="application/pdf",
    #         data=pdf_bytes
    #     )
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
        
    except Exception as e:
        current_app.logger.error(f"Error en new_orden_pago: {e}", exc_info=True)
        flash(f"Error al crear la orden de pago: {str(e)}", "danger")
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
    
    # Intentar cache primero
    cached_results = get_select2_cached_results("proveedores", term)
    if cached_results is not None:
        return jsonify({"results": cached_results})
    
    # Consulta optimizada
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
    
    # Cachear resultados
    if results:
        cache_select2_results("proveedores", term, results)
    
    return jsonify({"results": results})

@bp.route("/api/trabajadores")
def api_trabajadores():
    supabase = current_app.config["SUPABASE"]
    term = request.args.get("term", "")
    if not term:
        return jsonify({"results": []})
    
    # Intentar cache primero
    cached_results = get_select2_cached_results("trabajadores", term)
    if cached_results is not None:
        return jsonify({"results": cached_results})
    
    # Consulta optimizada
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
    
    # Cachear resultados
    if results:
        cache_select2_results("trabajadores", term, results)
    
    return jsonify({"results": results})

@bp.route("/check_iva/<int:oc_numero>", methods=["GET"])
def check_iva(oc_numero):
    """Verifica si una orden de compra específica es sin IVA"""
    supabase = current_app.config["SUPABASE"]
    
    try:
        # Consultar si la orden de compra es sin IVA
        oc_res = supabase.table("orden_de_compra") \
            .select("fac_sin_iva") \
            .eq("orden_compra", oc_numero) \
            .limit(1) \
            .execute()
        
        if oc_res.data and len(oc_res.data) > 0:
            sin_iva = bool(oc_res.data[0].get("fac_sin_iva", 0))
            return jsonify({"sin_iva": sin_iva})
        else:
            return jsonify({"sin_iva": False})
            
    except Exception as e:
        current_app.logger.error(f"Error verificando IVA para OC {oc_numero}: {e}")
        return jsonify({"sin_iva": False})