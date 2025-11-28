"""
API REST para Documentos Pendientes (Órdenes de Pago sin factura)
"""
from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required

bp = Blueprint("documentos_pendientes", __name__)


@bp.route("/", methods=["GET"])
@token_required
def list_pendientes(current_user):
    """
    Lista todas las órdenes de pago con estado_documento = 'pendiente'
    """
    supabase = current_app.config['SUPABASE']
    
    try:
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

        grouped = {}
        for l in all_lines:
            oc = l["orden_compra"]
            if oc not in grouped:
                grouped[oc] = []
            grouped[oc].append(l)

        filas = []
        for oc, lines in grouped.items():
            first = lines[0]
            materiales = [str(l.get("material_nombre") or "") for l in lines]
            resumen = ", ".join([m for m in materiales if m])
            if len(resumen) > 50:
                resumen = resumen[:47] + "..."
            
            total_costo = sum(float(l.get("costo_final_con_iva", 0) or 0) for l in lines)
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

        stats = {
            'total_pendientes': len(filas),
            'total_monto': sum(float(f.get('costo_final_con_iva', 0) or 0) for f in filas),
            'proveedores_unicos': len(set(f['proveedor_nombre'] for f in filas)),
            'ordenes_unicas': len(set(f['orden_numero'] for f in filas))
        }

        oc_list = list(grouped.keys())
        fac_pendientes_map = {}
        if oc_list:
            try:
                ingresos = (
                    supabase
                    .table("ingresos")
                    .select("orden_compra, fac_pendiente")
                    .in_("orden_compra", oc_list)
                    .execute()
                    .data or []
                )
                # Filtrar los que tienen fac_pendiente = '1' o 1
                for ing in ingresos:
                    fac_pend = ing.get('fac_pendiente')
                    if fac_pend in ('1', 1, True):
                        oc = ing.get('orden_compra')
                        if oc:
                            fac_pendientes_map[str(oc)] = True
            except Exception as ing_err:
                current_app.logger.warning(f"Error al consultar fac_pendiente: {ing_err}")
                # Continuar sin este dato
        
        for f in filas:
            f['fac_compra'] = fac_pendientes_map.get(str(f.get('orden_compra')), False)

        filas.sort(key=lambda f: f.get('orden_numero', 0), reverse=True)

        return jsonify({
            "success": True,
            "data": {
                "filas": filas,
                "stats": stats
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error al obtener documentos pendientes: {e}")
        return jsonify({
            "success": False, 
            "message": f"Error: {str(e)}"
        }), 500


@bp.route("/update", methods=["POST"])
@token_required
def update_pendiente(current_user):
    """
    Actualiza documento con número de factura
    """
    supabase = current_app.config['SUPABASE']
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "message": "No se recibieron datos"}), 400
    
    factura = data.get("factura", "").strip()
    if not factura:
        return jsonify({"success": False, "message": "Número de factura requerido"}), 400
    
    try:
        id_unico = data.get("id")
        ids_multiple = data.get("ids", [])
        
        current_app.logger.info(f"Actualizando documento: id={id_unico}, factura={factura}")
        
        if id_unico:
            result = (
                supabase
                .table("orden_de_pago")
                .update({"factura": factura, "estado_documento": "completado"})
                .eq("id", id_unico)
                .execute()
            )
            
            current_app.logger.info(f"Resultado actualización: {len(result.data) if result.data else 0} registros")
            
            if result.data:
                return jsonify({
                    "success": True, 
                    "message": f"Documento actualizado con factura {factura}"
                })
            else:
                return jsonify({"success": False, "message": "No se encontró el documento para actualizar"}), 404
                
        elif ids_multiple:
            for doc_id in ids_multiple:
                supabase.table("orden_de_pago").update({
                    "factura": factura,
                    "estado_documento": "completado"
                }).eq("id", doc_id).execute()
            
            return jsonify({
                "success": True,
                "message": f"{len(ids_multiple)} documento(s) actualizado(s)"
            })
        else:
            return jsonify({"success": False, "message": "Debe especificar 'id' o 'ids'"}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error al actualizar documento: {e}")
        return jsonify({
            "success": False, 
            "message": f"Error: {str(e)}"
        }), 500