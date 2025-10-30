import re
from datetime import date
from collections import defaultdict
from flask import Blueprint, request, jsonify, current_app, send_file
from io import BytesIO

# ========= Importaciones de Utilidades =========
from backend.utils.decorators import token_required
from backend.utils.cache import cache_result

bp = Blueprint("ordenes_pago", __name__)

# ========= Funciones Auxiliares =========

def normalize_text(text):
    """Normaliza texto para comparación"""
    if not text:
        return ''
    return ' '.join(str(text).replace('\n', ' ').split()).lower()


def parse_monto(x):
    """Convierte un string de moneda a float"""
    if not x:
        return 0.0
    limpio = re.sub(r'[^\d,\.]', '', str(x))
    partes = limpio.split(',')
    if len(partes) > 1:
        dec = partes[-1]
        ent = ''.join(partes[:-1])
        limpio2 = ent.replace('.', '') + '.' + dec
    else:
        limpio2 = partes[0].replace('.', '')
    try:
        return float(limpio2)
    except (ValueError, TypeError):
        return 0.0


# ================================================================
# ENDPOINT PRINCIPAL - OBTENER DOCUMENTOS PENDIENTES POR PROVEEDOR
# ================================================================

@bp.route("/", methods=["GET"])
@token_required
def get_documentos_pendientes(current_user):
    """
    Obtiene documentos pendientes de pago para un proveedor específico.
    Query params: proveedor_id (opcional)
    """
    supabase = current_app.config['SUPABASE']
    proveedor_id = request.args.get('proveedor_id', type=int)
    
    try:
        # 1. Obtener próximo número de orden de pago
        last_op = (
            supabase.table("orden_de_pago")
            .select("orden_numero")
            .order("orden_numero", desc=True)
            .limit(1)
            .execute().data or []
        )
        next_num = (last_op[0]["orden_numero"] + 1) if last_op else 1
        
        response_data = {
            "next_num": next_num,
            "proveedor_seleccionado": None,
            "documentos": []
        }
        
        if not proveedor_id:
            return jsonify({"success": True, "data": response_data})
        
        # 2. Obtener datos del proveedor
        prov = (
            supabase.table("proveedores")
            .select("id, nombre, rut, paguese_a, cuenta, banco, correo")
            .eq("id", proveedor_id)
            .limit(1)
            .execute().data or []
        )
        
        if not prov:
            return jsonify({"success": False, "message": "Proveedor no encontrado"}), 404
        
        response_data["proveedor_seleccionado"] = prov[0]
        
        # 3. Obtener todos los ingresos del proveedor
        ingresos = (
            supabase.table("ingresos")
            .select("id, orden_compra, factura, guia_recepcion, art_corr, neto_recepcion, material")
            .eq("proveedor", proveedor_id)
            .execute().data or []
        )
        
        # 4. Obtener IDs de ingresos ya usados en órdenes de pago
        ordenes_pago = (
            supabase.table("orden_de_pago")
            .select("ingreso_id")
            .eq("proveedor", proveedor_id)
            .execute().data or []
        )
        
        pagados_ids = {op["ingreso_id"] for op in ordenes_pago if op.get("ingreso_id")}
        
        # 5. Filtrar ingresos pendientes
        pendientes = [i for i in ingresos if i["id"] not in pagados_ids]
        
        # 6. Agrupar por factura + OC
        grupos = {}
        for ing in pendientes:
            factura_key = ing["factura"] if ing["factura"] else "SIN_DOCUMENTO"
            key = (factura_key, ing["orden_compra"])
            
            if key not in grupos:
                grupos[key] = {
                    "documento": factura_key,
                    "orden_compra": ing["orden_compra"],
                    "total_neto": 0.0,
                    "count": 0
                }
            
            grupos[key]["total_neto"] += float(ing.get("neto_recepcion") or 0)
            grupos[key]["count"] += 1
        
        # 7. Convertir a lista y ordenar
        documentos = list(grupos.values())
        documentos.sort(key=lambda d: d.get('orden_compra', 0), reverse=True)
        
        response_data["documentos"] = documentos
        
        return jsonify({"success": True, "data": response_data})
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener documentos pendientes: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# ================================================================
# ENDPOINT DETALLE - OBTENER LÍNEAS DE INGRESO
# ================================================================

@bp.route("/detalle", methods=["GET"])
@token_required
def get_detalle_documento(current_user):
    """
    Obtiene las líneas de ingreso para un documento específico.
    Query params: documento, oc, proveedor_id
    """
    supabase = current_app.config['SUPABASE']
    documento = request.args.get('documento')
    oc = request.args.get('oc', type=int)
    proveedor_id = request.args.get('proveedor_id', type=int)
    
    if not oc or not proveedor_id:
        return jsonify({"success": False, "message": "Parámetros incompletos"}), 400
    
    try:
        # 1. Construir query para ingresos
        query = (
            supabase.table("ingresos")
            .select("id, orden_compra, factura, guia_recepcion, art_corr, recepcion, neto_unitario, material")
            .eq("orden_compra", oc)
            .eq("proveedor", proveedor_id)
        )
        
        # Filtrar por documento
        if documento and documento != "SIN_DOCUMENTO":
            query = query.eq("factura", documento)
        else:
            query = query.or_("factura.is.null,factura.eq.")
        
        ingresos = query.execute().data or []
        
        # 2. Obtener IDs ya usados en órdenes de pago
        ordenes_pago = (
            supabase.table("orden_de_pago")
            .select("ingreso_id")
            .execute().data or []
        )
        
        pagados_ids = {op["ingreso_id"] for op in ordenes_pago if op.get("ingreso_id")}
        
        # 3. Obtener nombres de materiales
        mat_ids = {i["material"] for i in ingresos if i.get("material")}
        mat_map = {}
        
        if mat_ids:
            mats = (
                supabase.table("materiales")
                .select("id, material")
                .in_("id", list(mat_ids))
                .execute().data or []
            )
            mat_map = {m["id"]: m["material"] for m in mats}
        
        # 4. Construir resultado
        result = []
        for ing in ingresos:
            if ing["id"] in pagados_ids:
                continue
            
            material_nombre = mat_map.get(ing["material"], f"Material ID: {ing['material']}")
            
            result.append({
                "ingreso_id": ing["id"],
                "descripcion": material_nombre,
                "cantidad": int(ing.get("recepcion") or 0),
                "neto_unitario": float(ing.get("neto_unitario") or 0),
                "neto_total": int(ing.get("recepcion") or 0) * float(ing.get("neto_unitario") or 0),
                "art_corr": ing.get("art_corr"),
                "orden_compra": ing.get("orden_compra"),
                "material_id": ing.get("material"),
                "documento": ing.get("factura") or "SIN_DOCUMENTO"
            })
        
        return jsonify({"success": True, "data": result})
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener detalle: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# ================================================================
# ENDPOINT CREAR ORDEN DE PAGO
# ================================================================

@bp.route("/", methods=["POST"])
@token_required
def create_orden_pago(current_user):
    """
    Crea una nueva orden de pago con las líneas seleccionadas.
    """
    data = request.get_json()
    supabase = current_app.config['SUPABASE']
    
    try:
        # 1. Validar datos requeridos
        orden_numero = data.get("orden_numero")
        proveedor_id = data.get("proveedor_id")
        proveedor_nombre = data.get("proveedor_nombre")
        autoriza_id = data.get("autoriza_id")
        autoriza_nombre = data.get("autoriza_nombre")
        fecha_factura = data.get("fecha_factura")
        vencimiento = data.get("vencimiento")
        estado_pago = data.get("estado_pago", "")
        detalle_compra = data.get("detalle_compra", "").strip()
        lineas = data.get("lineas", [])
        
        if not all([orden_numero, proveedor_id, autoriza_id, fecha_factura, vencimiento]):
            return jsonify({"success": False, "message": "Faltan datos requeridos"}), 400
        
        if not detalle_compra:
            return jsonify({"success": False, "message": "El detalle de compra es obligatorio"}), 400
        
        if not lineas:
            return jsonify({"success": False, "message": "Debe seleccionar al menos una línea"}), 400
        
        # 2. Obtener próximo n_ingreso
        last_ingreso = (
            supabase.table("orden_de_pago")
            .select("n_ingreso")
            .order("n_ingreso", desc=True)
            .limit(1)
            .execute().data or []
        )
        n_ingreso = (last_ingreso[0]["n_ingreso"] if last_ingreso else 0) + 1
        
        # 3. Fecha actual
        hoy = date.today().isoformat()
        anio = date.today().year
        
        # 4. Preparar registros para inserción
        registros = []
        
        for linea in lineas:
            ingreso_id = linea.get("ingreso_id")
            oc_numero = linea.get("orden_compra")
            art_corr = linea.get("art_corr")
            material_id = linea.get("material_id")
            descripcion = linea.get("descripcion")
            cantidad = int(linea.get("cantidad") or 0)
            neto_unitario = float(linea.get("neto_unitario") or 0)
            documento = linea.get("documento")
            
            # Obtener datos de la OC
            oc_data = (
                supabase.table("orden_de_compra")
                .select("id, proyecto, condicion_de_pago, fac_sin_iva")
                .eq("orden_compra", oc_numero)
                .eq("art_corr", art_corr)
                .limit(1)
                .execute().data or []
            )
            
            if not oc_data:
                current_app.logger.warning(f"OC {oc_numero} art_corr {art_corr} no encontrada")
                continue
            
            oc = oc_data[0]
            orden_compra_id = oc["id"]
            proyecto = oc.get("proyecto")
            condicion_pago = oc.get("condicion_de_pago")
            fac_sin_iva = oc.get("fac_sin_iva", 0)
            
            # Obtener tipo e item del material
            mat_data = (
                supabase.table("materiales")
                .select("tipo, item")
                .eq("id", material_id)
                .limit(1)
                .execute().data or []
            )
            
            tipo_val = mat_data[0].get("tipo") if mat_data else None
            item_val = mat_data[0].get("item") if mat_data else None
            
            # Calcular totales
            neto_total = cantidad * neto_unitario
            costo_final = neto_total if fac_sin_iva else neto_total * 1.19
            
            # Estado del documento
            estado_doc = "completado" if documento and documento != "SIN_DOCUMENTO" else "pendiente"
            factura_val = documento if documento != "SIN_DOCUMENTO" else ""
            
            # Construir registro
            registros.append({
                "ingreso_id": ingreso_id,
                "orden_compra": orden_compra_id,  # FK al ID de orden_de_compra
                "doc_recep": documento or "",
                "art_corr": art_corr,
                "material": material_id,
                "material_nombre": descripcion,
                "cantidad": cantidad,
                "neto_unitario": neto_unitario,
                "neto_total_recibido": neto_total,
                "costo_final_con_iva": costo_final,
                "orden_numero": orden_numero,
                "proveedor": proveedor_id,
                "proveedor_nombre": proveedor_nombre,
                "autoriza": autoriza_id,
                "autoriza_nombre": autoriza_nombre,
                "fecha_factura": fecha_factura,
                "vencimiento": vencimiento,
                "estado_pago": estado_pago,
                "detalle_compra": detalle_compra,
                "proyecto": proyecto,
                "condicion_pago": condicion_pago,
                "factura": factura_val,
                "estado_documento": estado_doc,
                "tipo": tipo_val,
                "item": item_val,
                "fecha": hoy,
                "anio": anio,
                "n_ingreso": n_ingreso
            })
            
            n_ingreso += 1
        
        # 5. Insertar registros
        if not registros:
            return jsonify({"success": False, "message": "No se generaron registros válidos"}), 400
        
        result = supabase.table("orden_de_pago").insert(registros).execute()
        
        if result.data:
            return jsonify({
                "success": True,
                "message": f"Orden de Pago Nº{orden_numero} creada con {len(registros)} línea(s)",
                "orden_numero": orden_numero,
                "n_registros": len(registros)
            })
        else:
            return jsonify({"success": False, "message": "Error al insertar registros"}), 500
        
    except Exception as e:
        current_app.logger.error(f"Error al crear orden de pago: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# ================================================================
# ENDPOINT COPIAR ORDEN DE PAGO
# ================================================================

@bp.route("/copiar/<int:orden_numero>", methods=["GET"])
@token_required
def copiar_orden_pago(current_user, orden_numero):
    """
    Obtiene los datos de una orden de pago existente para copiarla.
    """
    supabase = current_app.config['SUPABASE']
    
    try:
        # Obtener todas las líneas de la orden de pago
        lineas = (
            supabase.table("orden_de_pago")
            .select("*")
            .eq("orden_numero", orden_numero)
            .execute().data or []
        )
        
        if not lineas:
            return jsonify({"success": False, "message": f"Orden {orden_numero} no encontrada"}), 404
        
        # Tomar datos del encabezado de la primera línea
        primera = lineas[0]
        
        # Obtener próximo número
        last_op = (
            supabase.table("orden_de_pago")
            .select("orden_numero")
            .order("orden_numero", desc=True)
            .limit(1)
            .execute().data or []
        )
        next_num = (last_op[0]["orden_numero"] + 1) if last_op else 1
        
        # Construir respuesta
        response = {
            "next_num": next_num,
            "proveedor_id": primera.get("proveedor"),
            "proveedor_nombre": primera.get("proveedor_nombre"),
            "autoriza_id": primera.get("autoriza"),
            "autoriza_nombre": primera.get("autoriza_nombre"),
            "fecha_factura": primera.get("fecha_factura"),
            "vencimiento": primera.get("vencimiento"),
            "estado_pago": primera.get("estado_pago", ""),
            "detalle_compra": primera.get("detalle_compra", ""),
            "lineas": []
        }
        
        # Procesar líneas
        for linea in lineas:
            response["lineas"].append({
                "descripcion": linea.get("material_nombre"),
                "cantidad": linea.get("cantidad"),
                "neto_unitario": linea.get("neto_unitario"),
                "neto_total": linea.get("neto_total_recibido"),
                "orden_compra": linea.get("orden_compra"),
                "documento": linea.get("factura") or "SIN_DOCUMENTO",
                "art_corr": linea.get("art_corr"),
                "material_id": linea.get("material")
            })
        
        return jsonify({"success": True, "data": response})
        
    except Exception as e:
        current_app.logger.error(f"Error al copiar orden {orden_numero}: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# ================================================================
# ENDPOINT HISTORIAL DE ÓRDENES
# ================================================================

@bp.route("/historial", methods=["GET"])
@token_required
# @cache_result(ttl_seconds=60)  # Cache comentado: causa error de serialización con User
def get_historial_ordenes(current_user):
    """
    Obtiene el historial de órdenes de pago creadas.
    """
    supabase = current_app.config['SUPABASE']
    
    try:
        # Obtener todas las órdenes agrupadas
        ordenes = (
            supabase.table("orden_de_pago")
            .select("orden_numero, proveedor_nombre, fecha, estado_pago, estado_documento")
            .order("orden_numero", desc=True)
            .execute().data or []
        )
        
        # Agrupar por orden_numero
        ordenes_agrupadas = {}
        for op in ordenes:
            num = op["orden_numero"]
            if num not in ordenes_agrupadas:
                ordenes_agrupadas[num] = {
                    "orden_numero": num,
                    "proveedor": op["proveedor_nombre"],
                    "fecha": op["fecha"],
                    "estado_pago": op["estado_pago"],
                    "estado_documento": op["estado_documento"],
                    "total": 0,
                    "lineas": 0
                }
        
        # Calcular totales
        for op in ordenes:
            num = op["orden_numero"]
            ordenes_agrupadas[num]["lineas"] += 1
        
        # Calcular totales monetarios
        for num in ordenes_agrupadas.keys():
            lineas_orden = [op for op in ordenes if op["orden_numero"] == num]
            total = 0
            for linea in lineas_orden:
                # Obtener el total de cada línea
                linea_data = (
                    supabase.table("orden_de_pago")
                    .select("costo_final_con_iva")
                    .eq("orden_numero", num)
                    .execute().data or []
                )
                for ld in linea_data:
                    total += float(ld.get("costo_final_con_iva") or 0)
            
            ordenes_agrupadas[num]["total"] = total
        
        # Convertir a lista
        resultado = list(ordenes_agrupadas.values())
        resultado.sort(key=lambda x: x["orden_numero"], reverse=True)
        
        return jsonify({"success": True, "data": resultado})
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener historial: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# ================================================================
# ENDPOINT DOCUMENTOS PENDIENTES (para completar)
# ================================================================

@bp.route("/pendientes", methods=["GET"])
@token_required
def get_documentos_pendientes_completar(current_user):
    """
    Obtiene órdenes de pago con documentos pendientes de completar.
    """
    supabase = current_app.config['SUPABASE']
    
    try:
        # Obtener órdenes con estado_documento = pendiente
        pendientes = (
            supabase.table("orden_de_pago")
            .select("id, orden_numero, orden_compra, proveedor_nombre, material_nombre, cantidad, neto_total_recibido, fecha, detalle_compra, factura")
            .eq("estado_documento", "pendiente")
            .order("orden_numero", desc=True)
            .execute().data or []
        )
        
        # Obtener números de OC reales (no IDs)
        for pend in pendientes:
            oc_id = pend.get("orden_compra")
            if oc_id:
                oc_data = (
                    supabase.table("orden_de_compra")
                    .select("orden_compra")
                    .eq("id", oc_id)
                    .limit(1)
                    .execute().data or []
                )
                if oc_data:
                    pend["orden_compra_numero"] = oc_data[0]["orden_compra"]
                else:
                    pend["orden_compra_numero"] = "N/A"
        
        return jsonify({"success": True, "data": pendientes})
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener pendientes: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/pendientes/<int:id>", methods=["PUT"])
@token_required
def completar_documento_pendiente(current_user, id):
    """
    Completa el documento de una orden de pago pendiente.
    """
    data = request.get_json()
    supabase = current_app.config['SUPABASE']
    factura = data.get("factura", "").strip()
    
    if not factura:
        return jsonify({"success": False, "message": "Número de documento requerido"}), 400
    
    try:
        # Actualizar registro
        result = (
            supabase.table("orden_de_pago")
            .update({"factura": factura, "estado_documento": "completado"})
            .eq("id", id)
            .execute()
        )
        
        if result.data:
            return jsonify({"success": True, "message": "Documento actualizado correctamente"})
        else:
            return jsonify({"success": False, "message": "No se pudo actualizar"}), 500
        
    except Exception as e:
        current_app.logger.error(f"Error al completar documento {id}: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# ================================================================
# ENDPOINTS AUXILIARES
# ================================================================

@bp.route("/helpers/check-iva/<int:oc_numero>", methods=["GET"])
@token_required
def check_iva_oc(current_user, oc_numero):
    """
    Verifica si una OC específica es sin IVA.
    """
    supabase = current_app.config['SUPABASE']
    
    try:
        oc = (
            supabase.table("orden_de_compra")
            .select("fac_sin_iva")
            .eq("orden_compra", oc_numero)
            .limit(1)
            .execute().data or []
        )
        
        sin_iva = bool(oc[0].get("fac_sin_iva", 0)) if oc else False
        
        return jsonify({"success": True, "sin_iva": sin_iva})
        
    except Exception as e:
        current_app.logger.error(f"Error al verificar IVA OC {oc_numero}: {str(e)}")
        return jsonify({"success": False, "sin_iva": False}), 500


# ================================================================
# ENDPOINT GENERAR PDF
# ================================================================

@bp.route("/pdf/<int:orden_numero>", methods=["GET"])
@token_required
def generar_pdf_orden(current_user, orden_numero):
    """
    Genera PDF de una orden de pago usando ReportLab.
    """
    supabase = current_app.config['SUPABASE']
    
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        
        # Obtener datos de la orden
        lineas = (
            supabase.table("orden_de_pago")
            .select("*")
            .eq("orden_numero", orden_numero)
            .execute().data or []
        )
        
        if not lineas:
            return jsonify({"success": False, "message": "Orden no encontrada"}), 404
        
        # Datos del encabezado
        primera = lineas[0]
        
        # Crear PDF en memoria
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()
        
        # Estilo personalizado para título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        # Título
        story.append(Paragraph(f"<b>Orden de Pago #{orden_numero}</b>", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Información de la empresa (encabezado)
        empresa_data = [
            ["SOMYL S.A."],
            ["RUT: 76.002.581-K"],
            ["TELECOMUNICACIONES"],
            ["PUERTA ORIENTE 361 OF 311 B TORRE B COLINA"],
            ["Tel: 232642974"]
        ]
        
        empresa_table = Table(empresa_data, colWidths=[6*inch])
        empresa_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        story.append(empresa_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Información del proveedor y detalles
        info_data = [
            ["<b>Páguese a:</b>", primera.get("proveedor_nombre", "")],
            ["<b>Autorizado por:</b>", primera.get("autoriza_nombre", "")],
            ["<b>Fecha Factura:</b>", primera.get("fecha_factura", "")],
            ["<b>Vencimiento:</b>", primera.get("vencimiento", "")],
            ["<b>Estado de Pago:</b>", primera.get("estado_pago", "")],
            ["<b>Detalle:</b>", primera.get("detalle_compra", "")],
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Tabla de materiales
        material_data = [["Descripción", "Cantidad", "Neto Unit.", "Total Neto"]]
        
        total_neto = 0
        total_iva = 0
        
        for linea in lineas:
            desc = linea.get("material_nombre", "")
            cant = linea.get("cantidad", 0)
            neto_u = linea.get("neto_unitario", 0)
            neto_t = linea.get("neto_total_recibido", 0)
            
            material_data.append([
                desc,
                str(cant),
                f"${neto_u:,.0f}",
                f"${neto_t:,.0f}"
            ])
            
            total_neto += neto_t
        
        # Verificar si es sin IVA
        oc_numero_check = lineas[0].get("orden_compra")
        sin_iva = False
        if oc_numero_check:
            oc_check = (
                supabase.table("orden_de_compra")
                .select("fac_sin_iva")
                .eq("id", oc_numero_check)
                .limit(1)
                .execute().data or []
            )
            sin_iva = bool(oc_check[0].get("fac_sin_iva", 0)) if oc_check else False
        
        total_iva = 0 if sin_iva else total_neto * 0.19
        total_final = total_neto + total_iva
        
        material_table = Table(material_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
        material_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        story.append(material_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Totales
        totales_data = [
            ["<b>Total Neto:</b>", f"${total_neto:,.0f}"],
            [f"<b>IVA (19%){'- EXENTO' if sin_iva else ''}:</b>", f"${total_iva:,.0f}"],
            ["<b>Total a Pagar:</b>", f"<b>${total_final:,.0f}</b>"]
        ]
        
        totales_table = Table(totales_data, colWidths=[4*inch, 2*inch])
        totales_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
        ]))
        story.append(totales_table)
        
        # Generar PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'orden_pago_{orden_numero}.pdf'
        )
        
    except ImportError:
        return jsonify({
            "success": False,
            "message": "ReportLab no está instalado. Ejecute: pip install reportlab"
        }), 500
    except Exception as e:
        current_app.logger.error(f"Error al generar PDF: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500