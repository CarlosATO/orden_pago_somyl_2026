from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    current_app,
    jsonify
)
from flask_login import login_required
from datetime import datetime
from app.modules.usuarios import require_modulo

bp_pending = Blueprint(
    "ordenes_pago_pendientes", __name__,
    template_folder="../templates/ordenes_pago"
)

@login_required
@bp_pending.route("/pendientes", methods=["GET"])
@require_modulo('orden_de_pago')
def list_pendientes():
    """
    Muestra todas las líneas de orden_de_pago con estado_documento = 'pendiente'.
    """
    supabase = current_app.config["SUPABASE"]
    
    try:
        # Consultar filas pendientes con más información
        filas = (
            supabase
            .table("orden_de_pago")
            .select(
                "id, orden_compra, orden_numero, proveedor_nombre, proveedor, "
                "material_nombre, cantidad, detalle_compra, fecha, "
                "neto_total_recibido, costo_final_con_iva"
            )
            .eq("estado_documento", "pendiente")
            .order("orden_numero", desc=False)
            .execute()
            .data
        ) or []
        
        current_app.logger.info(f"Documentos pendientes encontrados: {len(filas)}")
        
        # Agrupar estadísticas
        stats = {
            'total_pendientes': len(filas),
            'total_monto': sum(float(f.get('costo_final_con_iva', 0) or 0) for f in filas),
            'proveedores_unicos': len(set(f['proveedor_nombre'] for f in filas)),
            'ordenes_unicas': len(set(f['orden_numero'] for f in filas))
        }
        
        return render_template(
            "ordenes_pago/pendientes.html",
            filas=filas,
            stats=stats,
            fecha_actualizacion=datetime.now().strftime('%d/%m/%Y %H:%M')
        )
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener documentos pendientes: {e}")
        flash("Error al cargar documentos pendientes", "danger")
        return render_template(
            "ordenes_pago/pendientes.html",
            filas=[],
            stats={'total_pendientes': 0, 'total_monto': 0, 'proveedores_unicos': 0, 'ordenes_unicas': 0},
            fecha_actualizacion=datetime.now().strftime('%d/%m/%Y %H:%M')
        )

@login_required
@bp_pending.route("/pendientes/update", methods=["POST"])
@require_modulo('orden_de_pago')
def update_pendiente():
    """
    Actualiza una o varias líneas pendientes con el número de factura.
    Maneja tanto JSON (AJAX) como form data.
    """
    supabase = current_app.config["SUPABASE"]
    
    try:
        # Si es AJAX JSON
        if request.is_json:
            data = request.get_json()
            updates = data.get("updates", [])
            results = []
            
            current_app.logger.info(f"Procesando {len(updates)} actualizaciones via AJAX")
            
            for upd in updates:
                op_id = upd.get("id")
                factura = upd.get("factura", "").strip()
                proveedor_nombre = upd.get("proveedor_nombre", "").strip()
                
                # Validaciones
                if not op_id:
                    results.append({"id": op_id, "success": False, "msg": "ID de orden requerido"})
                    continue
                    
                if not factura or not factura.isdigit() or int(factura) <= 0:
                    results.append({"id": op_id, "success": False, "msg": "Número de documento inválido"})
                    continue
                
                try:
                    # Verificar que la orden existe y está pendiente
                    orden_actual = (
                        supabase
                        .table("orden_de_pago")
                        .select("id, proveedor_nombre, estado_documento")
                        .eq("id", op_id)
                        .single()
                        .execute()
                    )
                    
                    if not orden_actual.data:
                        results.append({"id": op_id, "success": False, "msg": "Orden no encontrada"})
                        continue
                        
                    if orden_actual.data.get("estado_documento") != "pendiente":
                        results.append({"id": op_id, "success": False, "msg": "Orden ya procesada"})
                        continue
                    
                    # Validar duplicado de factura para el mismo proveedor
                    duplicado = (
                        supabase
                        .table("orden_de_pago")
                        .select("id")
                        .eq("proveedor_nombre", proveedor_nombre)
                        .eq("factura", factura)
                        .neq("id", op_id)
                        .execute()
                        .data
                    )
                    
                    if duplicado:
                        results.append({
                            "id": op_id, 
                            "success": False, 
                            "msg": f"El documento {factura} ya existe para este proveedor"
                        })
                        continue
                    
                    # Actualizar la orden
                    update_result = (
                        supabase
                        .table("orden_de_pago")
                        .update({
                            "factura": factura,
                            "estado_documento": "completado"
                        })
                        .eq("id", op_id)
                        .execute()
                    )
                    
                    if update_result.data:
                        results.append({"id": op_id, "success": True, "msg": "Documento guardado exitosamente"})
                        current_app.logger.info(f"Documento actualizado: OP={op_id}, Factura={factura}")
                    else:
                        results.append({"id": op_id, "success": False, "msg": "Error al actualizar documento"})
                        
                except Exception as e:
                    current_app.logger.error(f"Error al procesar actualización {op_id}: {e}")
                    results.append({"id": op_id, "success": False, "msg": "Error interno del servidor"})
            
            return jsonify(results)

        # Si es form normal (fallback)
        else:
            ids = request.form.getlist("id[]")
            nums = request.form.getlist("factura[]")
            success_count = 0
            error_count = 0
            
            for i, op_id in enumerate(ids):
                factura = nums[i].strip() if i < len(nums) else ""
                
                if not factura or not factura.isdigit() or int(factura) <= 0:
                    flash(f"Documento inválido para línea {op_id}", "danger")
                    error_count += 1
                    continue
                
                try:
                    # Actualizar sin validaciones exhaustivas (para compatibilidad)
                    supabase.table("orden_de_pago")\
                        .update({"factura": factura, "estado_documento": "completado"})\
                        .eq("id", int(op_id))\
                        .execute()
                    success_count += 1
                except Exception as e:
                    current_app.logger.error(f"Error al actualizar línea {op_id}: {e}")
                    error_count += 1
            
            if error_count > 0:
                flash(f"Algunas líneas no se pudieron actualizar ({error_count} errores)", "warning")
            if success_count > 0:
                flash(f"{success_count} documento(s) actualizado(s) con éxito", "success")
            
            return redirect(url_for("ordenes_pago_pendientes.list_pendientes"))
            
    except Exception as e:
        current_app.logger.error(f"Error general en update_pendiente: {e}")
        if request.is_json:
            return jsonify([{"success": False, "msg": "Error interno del servidor"}]), 500
        else:
            flash("Error interno del servidor", "danger")
            return redirect(url_for("ordenes_pago_pendientes.list_pendientes"))
