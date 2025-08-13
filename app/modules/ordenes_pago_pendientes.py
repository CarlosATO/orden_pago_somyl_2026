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
from flask_login import current_user
from utils.logger import registrar_log_actividad

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

        # 1. Traer todas las líneas pendientes
        all_lines = (
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

        # 2. Agrupar por orden_compra
        grouped = {}
        for l in all_lines:
            oc = l["orden_compra"]
            if oc not in grouped:
                grouped[oc] = []
            grouped[oc].append(l)

        filas = []
        for oc, lines in grouped.items():
            first = lines[0]
            # Resumen de materiales
            materiales = [str(l.get("material_nombre") or "") for l in lines]
            resumen = ", ".join([m for m in materiales if m])
            if len(resumen) > 50:
                resumen = resumen[:47] + "..."
            # Sumar totales
            total_costo = sum(float(l.get("costo_final_con_iva", 0) or 0) for l in lines)
            # Obtener monto neto OC (suma de todas las líneas de la orden de pago)
            monto_neto_oc = sum(float(l.get("costo_final_con_iva", 0) or 0) for l in lines)
            fecha_op = first.get("fecha", "")
            fila = {
            **first,
            "material_nombre": resumen,
            "costo_final_con_iva": total_costo,
            "ids": [l["id"] for l in lines],
            "monto_neto_oc": monto_neto_oc,
            "fecha_op": fecha_op,
            }
            filas.append(fila)

        current_app.logger.info(f"Órdenes pendientes encontradas: {len(filas)}")

        # Estadísticas por orden
        stats = {
            'total_pendientes': len(filas),
            'total_monto': sum(float(f.get('costo_final_con_iva', 0) or 0) for f in filas),
            'proveedores_unicos': len(set(f['proveedor_nombre'] for f in filas)),
            'ordenes_unicas': len(set(f['orden_numero'] for f in filas))
        }

        # Buscar OC únicas para consulta eficiente
        oc_list = list(grouped.keys())
        fac_pendientes_map = {}
        if oc_list:
            ingresos = (
                supabase
                .table("ingresos")
                .select("orden_compra, fac_pendiente")
                .in_("orden_compra", oc_list)
                .eq("fac_pendiente", 1)
                .execute()
                .data or []
            )
            for ing in ingresos:
                oc = ing.get('orden_compra')
                if oc:
                    fac_pendientes_map[str(oc)] = True
        for f in filas:
            f['fac_compra'] = fac_pendientes_map.get(str(f.get('orden_compra')), False)

        filas.sort(key=lambda f: f.get('orden_numero', 0), reverse=True)
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
                orden_compra = upd.get("orden_compra")
                factura = upd.get("factura", "").strip()
                proveedor_nombre = upd.get("proveedor_nombre", "").strip()
                # Si no viene orden_compra, intentar obtenerla desde id
                if not orden_compra and upd.get("id"):
                    try:
                        res = supabase.table("orden_de_pago").select("orden_compra").eq("id", upd["id"]).single().execute()
                        orden_compra = res.data["orden_compra"] if res and res.data else None
                    except Exception as e:
                        current_app.logger.error(f"No se pudo obtener orden_compra desde id {upd.get('id')}: {e}")
                        orden_compra = None
                # Validaciones
                if not orden_compra:
                    results.append({"orden_compra": orden_compra, "success": False, "msg": "Orden de compra requerida"})
                    continue
                if not factura or not factura.isdigit() or int(factura) <= 0:
                    results.append({"orden_compra": orden_compra, "success": False, "msg": "Número de documento inválido"})
                    continue
                try:
                    # Verificar que la orden existe y está pendiente (al menos una línea)
                    pendientes = (
                        supabase
                        .table("orden_de_pago")
                        .select("id, proveedor_nombre, estado_documento")
                        .eq("orden_compra", orden_compra)
                        .eq("estado_documento", "pendiente")
                        .execute()
                        .data or []
                    )
                    if not pendientes:
                        results.append({"orden_compra": orden_compra, "success": False, "msg": "Orden no encontrada o ya procesada"})
                        continue
                    # Validar duplicado de factura para el mismo proveedor SOLO en pendientes
                    duplicado = (
                        supabase
                        .table("orden_de_pago")
                        .select("id")
                        .eq("proveedor_nombre", proveedor_nombre)
                        .eq("factura", factura)
                        .eq("estado_documento", "pendiente")
                        .execute()
                        .data
                    )
                    if duplicado:
                        results.append({
                            "orden_compra": orden_compra,
                            "success": False,
                            "msg": "Esta factura ya está registrada para este proveedor"
                        })
                        continue
                    # Actualizar todas las líneas de la orden
                    update_result = (
                        supabase
                        .table("orden_de_pago")
                        .update({
                            "factura": factura,
                            "estado_documento": "completado"
                        })
                        .eq("orden_compra", orden_compra)
                        .eq("estado_documento", "pendiente")
                        .execute()
                    )
                    if getattr(update_result, "data", None):
                        results.append({"orden_compra": orden_compra, "success": True, "msg": "Documento guardado exitosamente"})
                        current_app.logger.info(f"Documento actualizado: OC={orden_compra}, Factura={factura}")
                        # Log de actividad
                        for linea in pendientes:
                            registrar_log_actividad(
                                accion="actualizar",
                                tabla_afectada="orden_de_pago",
                                registro_id=linea["id"],
                                descripcion=f"Factura '{factura}' registrada para OC {orden_compra} (pendiente completado)",
                                datos_antes=linea,
                                datos_despues={**linea, "factura": factura, "estado_documento": "completado"}
                            )
                    else:
                        results.append({"orden_compra": orden_compra, "success": False, "msg": "Error al actualizar documento"})
                except Exception as e:
                    current_app.logger.error(f"Error al procesar actualización {orden_compra}: {e}")
                    results.append({"orden_compra": orden_compra, "success": False, "msg": "Error interno del servidor"})
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
