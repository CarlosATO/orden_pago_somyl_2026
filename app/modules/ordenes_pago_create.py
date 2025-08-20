from flask import Blueprint, request, jsonify, current_app, flash, redirect, url_for
from flask_login import current_user
from app.modules.enviar_correo import enviar_correo_con_pdfs
from utils.logger import registrar_log_actividad
from datetime import date

def proyectos_op_correo(supabase, ocs):
    """Obtiene nombres de proyectos asociados a las órdenes de compra para el correo"""
    # --- Obtener nombres de proyectos asociados a las OCs ---
    proyecto_ids = set()
    if ocs:
        oc_numbers = [int(oc) for oc in ocs if str(oc).isdigit()]
        # Paginación manual para orden_de_compra
        page_size = 1000
        offset = 0
        while True:
            batch = (
                supabase.table('orden_de_compra')
                    .select('orden_compra, proyecto')
                    .in_('orden_compra', oc_numbers)
                    .range(offset, offset + page_size - 1)
                    .execute()
                    .data or []
            )
            for row in batch:
                pid = row.get('proyecto')
                if pid:
                    proyecto_ids.add(pid)
            if len(batch) < page_size:
                break
            offset += page_size

    # Buscar nombres de proyectos en tabla proyectos
    proyectos_nombres = set()
    if proyecto_ids:
        page_size = 1000
        offset = 0
        ids_list = list(proyecto_ids)
        while True:
            batch = (
                supabase.table('proyectos')
                    .select('id, proyecto')
                    .in_('id', ids_list)
                    .range(offset, offset + page_size - 1)
                    .execute()
                    .data or []
            )
            for row in batch:
                nombre = row.get('proyecto')
                if nombre:
                    proyectos_nombres.add(nombre)
            if len(batch) < page_size:
                break
            offset += page_size
    if not proyectos_nombres:
        proyectos_nombres = {'Sin proyecto'}
    proyectos_str = ' - '.join(sorted(proyectos_nombres, key=lambda x: x.lower()))
    return proyectos_str

bp_ordenes_pago_create = Blueprint('ordenes_pago_create', __name__)

@bp_ordenes_pago_create.route('/api/enviar-correo', methods=['POST'])
def api_enviar_correo():
    try:
        import os
        supabase = current_app.config['SUPABASE']
        
        # Obtener datos del formulario
        orden_id = request.form.get('orden_id')
        nombre_proveedor = request.form.get('nombre_proveedor', '')
        
        # Verificar que se haya proporcionado orden_id
        if not orden_id:
            return jsonify({"success": False, "msg": "ID de orden requerido"}), 400
            
        # Verificar que existan destinatarios activos antes de intentar enviar
        from app.modules.enviar_correo import obtener_destinatarios_activos
        destinatarios = obtener_destinatarios_activos(supabase)
        if not destinatarios:
            return jsonify({"success": False, "msg": "No hay destinatarios de correo configurados"}), 400
        
        # Buscar el PDF generado
        pdf_dir = os.path.join(current_app.root_path, 'static', 'ordenes_pago', 'generated_pdfs')
        pdf_files = []
        if os.path.exists(pdf_dir):
            for filename in os.listdir(pdf_dir):
                if filename.startswith(f"orden_pago_{orden_id}_") and filename.endswith('.pdf'):
                    pdf_path = os.path.join(pdf_dir, filename)
                    with open(pdf_path, 'rb') as f:
                        pdf_content = f.read()
                    pdf_files.append((pdf_content, filename))
                    break
        
        if not pdf_files:
            return jsonify({"success": False, "msg": "No se encontró el PDF generado. Genere el PDF primero."}), 400
        
        # Obtener documentos adjuntos opcionales
        doc1 = request.files.get('documento1')
        doc2 = request.files.get('documento2')
        
        pdf_opcional_1 = None
        pdf_opcional_2 = None
        
        if doc1 and doc1.filename:
            pdf_opcional_1 = (doc1.read(), doc1.filename)
        
        if doc2 and doc2.filename:
            pdf_opcional_2 = (doc2.read(), doc2.filename)
        
        # Obtener información del proyecto usando las órdenes de compra del formulario
        oc_list = request.form.getlist('orden_compra[]')
        proyecto_info = proyectos_op_correo(supabase, oc_list)
        
        # Crear asunto y cuerpo del correo con información del proyecto
        asunto = f"Orden de Pago #{orden_id} - {nombre_proveedor} - {proyecto_info}"
        cuerpo = f"""Estimada Cynthia,

Adjunto encontrará la Orden de Pago #{orden_id} correspondiente a:

• Proveedor: {nombre_proveedor}
• Proyecto: {proyecto_info}

Por favor, proceder con la revisión y procesamiento correspondiente.

Saludos cordiales,
Equipo Somyl"""
        
        # Enviar correo con todos los PDFs
        enviar_correo_con_pdfs(
            supabase,
            pdf_principal=pdf_files[0],
            pdf_opcional_1=pdf_opcional_1,
            pdf_opcional_2=pdf_opcional_2,
            asunto=asunto,
            cuerpo=cuerpo
        )
        
        # Contar total de archivos adjuntos
        total_archivos = 1  # PDF principal
        if pdf_opcional_1: total_archivos += 1
        if pdf_opcional_2: total_archivos += 1
        
        return jsonify({
            "success": True, 
            "msg": f"Correo con Orden de Pago #{orden_id} enviado correctamente a {len(destinatarios)} destinatario(s) con {total_archivos} archivo(s) adjunto(s)."
        })
    except Exception as e:
        current_app.logger.error(f"Error enviando correo: {str(e)}")
        return jsonify({"success": False, "msg": f"Error al enviar correo: {str(e)}"}), 500


# Función para crear orden de pago (funcionalidad original)
@bp_ordenes_pago_create.route('/ordenes_pago/create', methods=['POST'], endpoint='create')
def crear_orden_pago():
    supabase = current_app.config['SUPABASE']
    f = request.form

    # 1) Datos generales
    numero            = int(f['next_num'])
    nombre_proveedor  = f['nombre_proveedor']
    proveedor_id      = int(f['proveedor_id'])
    autoriza_id       = int(f['autoriza_id'])
    fecha_factura     = f['fecha_factura']
    fecha_vencimiento = f['fecha_vencimiento']
    estado_pago       = f.get('estado_pago', '')
    detalle_op        = f.get('detalle_op', '')

    # Fecha de creación (columna 'fecha')
    hoy = date.today().isoformat()

    # 2) Listas de detalle (todas vienen en paralelo)
    oc_list         = f.getlist('orden_compra[]')    # ej: ["7", "7", ...]
    guias           = f.getlist('guia_recepcion[]')  # ej: ["10", "10", ...]
    arts            = f.getlist('art_corr[]')        # ej: ["11", "12", ...]
    descripciones   = f.getlist('descripcion[]')
    recepciones     = f.getlist('recepcion[]')
    netos_unitarios = f.getlist('neto_unitario[]')
    totales_netos   = f.getlist('neto_total[]')

    # 3) Próximo n_ingreso en la tabla orden_de_pago (no confundir con orden_compra)
    resp = supabase.table('orden_de_pago') \
                   .select('n_ingreso') \
                   .order('n_ingreso', desc=True) \
                   .limit(1) \
                   .execute().data or []
    max_n = resp[0]['n_ingreso'] if resp else 0
    n_ingreso_next = max_n + 1

    # 4) Construir payload línea a línea
    payload = []
    for oc_numero, guia, art_corr, desc, cant, nu, tn in zip(
        oc_list, guias, arts, descripciones, recepciones, netos_unitarios, totales_netos
    ):
        # 4.0) Convertir a tipos adecuados:
        oc_int     = int(oc_numero)
        art_corr_i = int(art_corr)
        cant_i     = int(cant or 0)
        nu_f       = float(nu or 0)
        tn_f       = float(tn or 0)

        # 4.1) Buscamos en orden_de_compra la fila cuyo “número de orden” = oc_int
        #      y cuyo art_corr = art_corr_i, para obtener su id real:
        oc_row = (
            supabase.table('orden_de_compra')
                    .select('id')
                    .eq('orden_compra', oc_int)
                    .eq('art_corr', str(art_corr_i))  # art_corr está guardado como varchar
                    .limit(1)
                    .execute()
                    .data or []
        )
        if not oc_row:
            # Si no existe coincidencia, simplemente saltamos esa línea
            continue

        oc_real_id = oc_row[0]['id']  # este es el valor que la FK espera

        # 4.2) Ahora obtenemos proyecto de esa misma OC (podría venir previo, pero así garantizamos)
        proj_rows = supabase.table('orden_de_compra') \
                            .select('proyecto') \
                            .eq('id', oc_real_id) \
                            .limit(1) \
                            .execute().data or []
        proyecto_val = proj_rows[0].get('proyecto') if proj_rows else None

        # 4.3) Material → id, tipo, item
        mat_rows = supabase.table('materiales') \
                          .select('id, tipo, item') \
                          .eq('material', desc) \
                          .limit(1) \
                          .execute().data or []
        mat = mat_rows[0] if mat_rows else {}
        mat_id   = mat.get('id')
        tipo_val = mat.get('tipo', '')
        item_val = mat.get('item', '')

        # 4.4) Mes de la factura (puedes omitirlo, o usarlo si tu modelo lo requiere)
        mes = int(fecha_factura.split('-')[1])

        # 4.5) Agregar al payload, usando oc_real_id como la clave foránea
        payload.append({
            'orden_numero':         numero,
            'proveedor':            proveedor_id,
            'proveedor_nombre':     nombre_proveedor,
            'autoriza':             autoriza_id,
            'autoriza_nombre':      f.get('autoriza_input', ''),
            'fecha':                hoy,
            'fecha_factura':        fecha_factura,
            'vencimiento':          fecha_vencimiento,
            'estado_pago':          estado_pago,
            'detalle_compra':       detalle_op,
            'factura':              "-".join(dict.fromkeys(guias)),
            'doc_recep':            "-".join(dict.fromkeys(guias)),
            # — Aquí va el ID real, no el número de OC:
            'orden_compra':         oc_real_id,
            'material':             mat_id,
            'material_nombre':      desc,
            'cantidad':             cant_i,
            'neto_unitario':        nu_f,
            'neto_total_recibido':  tn_f,
            'costo_final_con_iva':  nu_f * cant_i * 1.19,
            'forma_pago':           '0',
            'item':                 tipo_val,
            'tipo':                 item_val,
            'mes':                  mes,
            'art_corr':             art_corr_i,
            'n_ingreso':            n_ingreso_next,
            'proyecto':             proyecto_val
        })

        # Aumentamos el consecutivo de ingreso para la siguiente línea
        n_ingreso_next += 1

    # 5) Validar payload
    if not payload:
        flash("No se seleccionó ninguna línea.", "warning")
        return redirect(url_for('ordenes_pago.list_ordenes_pago', nombre_proveedor=nombre_proveedor))

    # 6) Insertar todas las líneas del payload
    result = supabase.table('orden_de_pago').insert(payload).execute()
    # Log de actividad por cada línea insertada
    if hasattr(result, 'data') and result.data:
        for i, linea in enumerate(result.data):
            registrar_log_actividad(
                accion="crear",
                tabla_afectada="orden_de_pago",
                registro_id=linea.get("id"),
                descripcion=f"Orden de pago #{numero} creada (línea {i+1}) para proveedor {nombre_proveedor}.",
                datos_antes=None,
                datos_despues=payload[i] if i < len(payload) else None
            )
    flash(f"Orden de pago #{numero} creada con {len(payload)} línea(s).", "success")
    return redirect(url_for('ordenes_pago.list_ordenes_pago', nombre_proveedor=nombre_proveedor))