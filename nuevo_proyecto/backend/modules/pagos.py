# nuevo_proyecto/backend/modules/pagos.py

from flask import Blueprint, request, jsonify, current_app
from datetime import date, datetime, timedelta
from backend.utils.decorators import token_required
import logging

bp = Blueprint("pagos_api", __name__)
logger = logging.getLogger(__name__)

# ================================================================
# FUNCIONES AUXILIARES
# ================================================================

def get_cached_proveedores():
    """Obtener proveedores desde Supabase"""
    supabase = current_app.config['SUPABASE']
    try:
        result = supabase.table("proveedores").select("id, nombre, rut, cuenta").execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Error obteniendo proveedores: {e}")
        return []

def get_cached_proyectos():
    """Obtener proyectos desde Supabase"""
    supabase = current_app.config['SUPABASE']
    try:
        result = supabase.table("proyectos").select("id, proyecto").execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Error obteniendo proyectos: {e}")
        return []

def calcular_estado_pago(fecha_pago, total_abonado, total_pago):
    """Calcular estado del pago"""
    if fecha_pago:
        return "pagado"
    elif total_abonado > 0 and total_abonado < total_pago:
        return "abono"
    else:
        return "pendiente"

# ================================================================
# ENDPOINT PRINCIPAL - LISTAR PAGOS CON PAGINACIÓN
# ================================================================

@bp.route("/list", methods=["GET"])
@token_required
def list_pagos(current_user):
    """
    Obtiene lista de pagos con paginación de Supabase.
    """
    supabase = current_app.config['SUPABASE']
    
    # Función auxiliar para reintentos
    def execute_with_retry(query_func, max_retries=3):
        for attempt in range(max_retries):
            try:
                return query_func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Intento {attempt + 1} falló: {e}. Reintentando...")
                import time
                time.sleep(0.5 * (attempt + 1))  # Espera incremental
        return None
    
    try:
        # Parámetros de paginación
        page = max(1, request.args.get('page', 1, type=int))
        per_page = min(request.args.get('per_page', 50, type=int), 100)  # Reducido a 100
        
        # Filtros
        proveedor = request.args.get('proveedor', '').strip()
        proyecto_id = request.args.get('proyecto', '').strip()
        estado = request.args.get('estado', '').strip()
        fecha_desde = request.args.get('fecha_desde', '').strip()
        fecha_hasta = request.args.get('fecha_hasta', '').strip()
        orden_numero = request.args.get('orden_numero', '').strip()
        
        # Calcular offset
        offset = (page - 1) * per_page
        end_range = offset + per_page - 1
        
        # Query base con conteo - CON RETRY
        def build_query():
            query = supabase.table("orden_de_pago").select(
                "orden_numero, fecha, proveedor, proveedor_nombre, detalle_compra, "
                "factura, costo_final_con_iva, proyecto, orden_compra, condicion_pago, "
                "vencimiento, fecha_factura, ingreso_id",
                count="exact"
            )
            
            # Aplicar filtros
            if proveedor:
                query = query.ilike("proveedor_nombre", f"%{proveedor}%")
            
            if proyecto_id:
                try:
                    query = query.eq("proyecto", int(proyecto_id))
                except ValueError:
                    pass
            
            if fecha_desde:
                query = query.gte("fecha", fecha_desde)
            
            if fecha_hasta:
                query = query.lte("fecha", fecha_hasta)
            
            if orden_numero:
                try:
                    query = query.eq("orden_numero", int(orden_numero))
                except ValueError:
                    pass
            
            # Ejecutar query con paginación
            query = query.order("orden_numero", desc=True).range(offset, end_range)
            return query.execute()
        
        result = execute_with_retry(build_query)
        
        if not result:
            return jsonify({
                "success": False,
                "message": "Error de conexión con la base de datos"
            }), 503
        
        all_rows = result.data or []
        total_count = result.count or 0
        
        # Si no hay datos, retornar vacío
        if not all_rows:
            return jsonify({
                "success": True,
                "data": {
                    "pagos": [],
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total": 0,
                        "total_pages": 0
                    }
                }
            })
        
        # Agrupar por orden_numero
        pagos_dict = {}
        orden_numeros = []
        
        for r in all_rows:
            num = r["orden_numero"]
            if num not in pagos_dict:
                orden_numeros.append(num)
                pagos_dict[num] = {
                    "orden_numero": num,
                    "fecha": r["fecha"],
                    "proveedor": r.get("proveedor"),
                    "proveedor_nombre": r["proveedor_nombre"],
                    "detalle_compra": r["detalle_compra"],
                    "factura": r["factura"],
                    "total_pago": 0.0,
                    "proyecto": r["proyecto"],
                    "orden_compra": r["orden_compra"],
                    "condicion_pago": r["condicion_pago"],
                    "vencimiento": r["vencimiento"],
                    "fecha_factura": r["fecha_factura"],
                    "ingreso_id": r.get("ingreso_id"),
                    "fecha_pago": None,
                    "total_abonado": 0.0,
                    "saldo_pendiente": 0.0,
                    "item": "-",
                    "rut_proveedor": "-",
                    "fac_pago": ""
                }
            pagos_dict[num]["total_pago"] += float(r.get("costo_final_con_iva") or 0)
        
        pagos_list = list(pagos_dict.values())
        
        # Obtener datos relacionados EN LOTES PEQUEÑOS
        if orden_numeros:
            # Dividir en lotes de 20 para evitar sobrecarga
            batch_size = 20
            fecha_map = {}
            abonos_map = {}
            
            for i in range(0, len(orden_numeros), batch_size):
                batch = orden_numeros[i:i+batch_size]
                
                # Fechas de pago
                try:
                    fechas_result = execute_with_retry(
                        lambda: supabase.table("fechas_de_pagos_op").select(
                            "orden_numero, fecha_pago"
                        ).in_("orden_numero", batch).execute()
                    )
                    for r in (fechas_result.data or []):
                        fecha_map[r["orden_numero"]] = r["fecha_pago"]
                except Exception as e:
                    logger.error(f"Error obteniendo fechas: {e}")
                
                # Abonos
                try:
                    abonos_result = execute_with_retry(
                        lambda: supabase.table("abonos_op").select(
                            "orden_numero, monto_abono"
                        ).in_("orden_numero", batch).execute()
                    )
                    for ab in (abonos_result.data or []):
                        num = ab["orden_numero"]
                        abonos_map[num] = abonos_map.get(num, 0) + float(ab.get("monto_abono") or 0)
                except Exception as e:
                    logger.error(f"Error obteniendo abonos: {e}")
            
            # Proveedores y proyectos (cache simple)
            proveedores = get_cached_proveedores()
            proyectos = get_cached_proyectos()
            rut_map = {p["id"]: p.get("rut", "-") for p in proveedores}
            proyecto_map = {p["id"]: p["proyecto"] for p in proyectos}
            
            # Aplicar datos a cada pago
            for pago in pagos_list:
                num = pago["orden_numero"]
                pago["fecha_pago"] = fecha_map.get(num)
                pago["total_abonado"] = abonos_map.get(num, 0)
                pago["saldo_pendiente"] = 0 if pago["fecha_pago"] else max(
                    0, pago["total_pago"] - pago["total_abonado"]
                )
                pago["rut_proveedor"] = rut_map.get(pago.get("proveedor"), "-")
                pago["proyecto_nombre"] = proyecto_map.get(pago["proyecto"], f"Proyecto {pago['proyecto']}")
                pago["estado"] = calcular_estado_pago(
                    pago["fecha_pago"], 
                    pago["total_abonado"], 
                    pago["total_pago"]
                )
        
        # Filtro de estado (post-procesamiento)
        if estado:
            pagos_list = [p for p in pagos_list if p["estado"] == estado]
        
        # Calcular total de páginas
        total_pages = (total_count + per_page - 1) // per_page
        
        return jsonify({
            "success": True,
            "data": {
                "pagos": pagos_list,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_count,
                    "total_pages": total_pages
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error en list_pagos: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False, 
            "message": "Error interno del servidor. Intente nuevamente."
        }), 500

# ================================================================
# ENDPOINT - ESTADÍSTICAS
# ================================================================

@bp.route("/stats", methods=["GET"])
@token_required
def get_stats(current_user):
    """
    Obtiene estadísticas generales de pagos.
    Aplica los mismos filtros que list_pagos.
    """
    supabase = current_app.config['SUPABASE']
    
    try:
        # Filtros (mismos que list_pagos)
        proveedor = request.args.get('proveedor', '').strip()
        proyecto_id = request.args.get('proyecto', '').strip()
        fecha_desde = request.args.get('fecha_desde', '').strip()
        fecha_hasta = request.args.get('fecha_hasta', '').strip()
        
        # Query con filtros
        query = supabase.table("orden_de_pago").select(
            "orden_numero, costo_final_con_iva, proyecto",
            count="exact"
        )
        
        if proveedor:
            query = query.ilike("proveedor_nombre", f"%{proveedor}%")
        
        if proyecto_id:
            query = query.eq("proyecto", int(proyecto_id))
        
        if fecha_desde:
            query = query.gte("fecha", fecha_desde)
        
        if fecha_hasta:
            query = query.lte("fecha", fecha_hasta)
        
        result = query.execute()
        all_rows = result.data or []
        
        # Agrupar por orden_numero
        pagos_dict = {}
        for r in all_rows:
            num = r["orden_numero"]
            if num not in pagos_dict:
                pagos_dict[num] = {
                    "orden_numero": num,
                    "total_pago": 0.0,
                    "proyecto": r["proyecto"]
                }
            pagos_dict[num]["total_pago"] += float(r.get("costo_final_con_iva") or 0)
        
        orden_numeros = list(pagos_dict.keys())
        
        # Obtener fechas de pago y abonos
        fechas_pagadas = set()
        abonos_map = {}
        
        if orden_numeros:
            # Fechas
            fechas_result = supabase.table("fechas_de_pagos_op").select(
                "orden_numero"
            ).in_("orden_numero", orden_numeros).execute()
            
            fechas_pagadas = set(r["orden_numero"] for r in (fechas_result.data or []))
            
            # Abonos
            abonos_result = supabase.table("abonos_op").select(
                "orden_numero, monto_abono"
            ).in_("orden_numero", orden_numeros).execute()
            
            for ab in (abonos_result.data or []):
                num = ab["orden_numero"]
                abonos_map[num] = abonos_map.get(num, 0) + float(ab.get("monto_abono") or 0)
        
        # Calcular métricas
        total_ordenes = len(pagos_dict)
        pagadas = len(fechas_pagadas)
        pendientes = total_ordenes - pagadas
        
        total_pendiente = 0.0
        saldo_por_proyecto = {}
        
        # Proyectos
        proyectos = get_cached_proyectos()
        proyecto_map = {p["id"]: p["proyecto"] for p in proyectos}
        
        for num, pago in pagos_dict.items():
            if num not in fechas_pagadas:
                total_abonado = abonos_map.get(num, 0)
                saldo = pago["total_pago"] - total_abonado
                total_pendiente += saldo
                
                # Saldo por proyecto
                proyecto_nombre = proyecto_map.get(pago["proyecto"], str(pago["proyecto"]))
                saldo_por_proyecto[proyecto_nombre] = saldo_por_proyecto.get(
                    proyecto_nombre, 0
                ) + saldo
        
        # Filtrar proyectos con saldo > 1
        saldo_por_proyecto = {k: v for k, v in saldo_por_proyecto.items() if v > 1}
        
        return jsonify({
            "success": True,
            "data": {
                "total_ordenes": total_ordenes,
                "pagadas": pagadas,
                "pendientes": pendientes,
                "total_pendiente": total_pendiente,
                "saldo_por_proyecto": saldo_por_proyecto
            }
        })
        
    except Exception as e:
        logger.error(f"Error en get_stats: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# ================================================================
# ENDPOINT - ACTUALIZAR FECHA DE PAGO
# ================================================================

@bp.route("/fecha", methods=["PUT"])
@token_required
def update_fecha_pago(current_user):
    """
    Actualiza la fecha de pago de una orden.
    Body: { "orden_numero": 123, "fecha_pago": "2025-10-24" }
    """
    supabase = current_app.config['SUPABASE']
    
    try:
        data = request.get_json()
        orden_numero = data.get("orden_numero")
        fecha_pago = data.get("fecha_pago", "").strip()
        
        if not orden_numero:
            return jsonify({
                "success": False, 
                "message": "orden_numero requerido"
            }), 400
        
        # Validar fecha
        if fecha_pago:
            try:
                fecha_obj = datetime.strptime(fecha_pago, "%Y-%m-%d").date()
                if fecha_obj > date.today() + timedelta(days=7):
                    return jsonify({
                        "success": False,
                        "message": "Fecha de pago muy futura"
                    }), 400
            except ValueError:
                return jsonify({
                    "success": False,
                    "message": "Formato de fecha inválido"
                }), 400
            
            # Upsert fecha
            supabase.table("fechas_de_pagos_op").upsert({
                "orden_numero": orden_numero,
                "fecha_pago": fecha_pago
            }, on_conflict=["orden_numero"]).execute()
            
            return jsonify({
                "success": True,
                "message": "Fecha de pago actualizada"
            })
        else:
            # Eliminar fecha si está vacía (verificar abonos primero)
            abonos = supabase.table("abonos_op").select("id").eq(
                "orden_numero", orden_numero
            ).execute()
            
            if abonos.data:
                return jsonify({
                    "success": False,
                    "message": "No puedes borrar la fecha porque tiene abonos registrados"
                }), 400
            
            # Eliminar fecha
            supabase.table("fechas_de_pagos_op").delete().eq(
                "orden_numero", orden_numero
            ).execute()
            
            return jsonify({
                "success": True,
                "message": "Fecha de pago eliminada"
            })
        
    except Exception as e:
        logger.error(f"Error en update_fecha_pago: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# ================================================================
# ENDPOINT - OBTENER ABONOS DE UNA ORDEN
# ================================================================

@bp.route("/abonos/<int:orden_numero>", methods=["GET"])
@token_required
def get_abonos(current_user, orden_numero):
    """Obtiene todos los abonos de una orden"""
    supabase = current_app.config['SUPABASE']
    
    try:
        result = supabase.table("abonos_op").select(
            "id, orden_numero, monto_abono, fecha_abono, observacion"
        ).eq("orden_numero", orden_numero).order("fecha_abono", desc=True).execute()
        
        return jsonify({
            "success": True,
            "data": result.data or []
        })
        
    except Exception as e:
        logger.error(f"Error en get_abonos: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# ================================================================
# ENDPOINT - CREAR ABONO
# ================================================================

@bp.route("/abono", methods=["POST"])
@token_required
def create_abono(current_user):
    """
    Crea un nuevo abono.
    Body: {
        "orden_numero": 123,
        "monto_abono": 50000,
        "fecha_abono": "2025-10-24",
        "observacion": "Abono parcial"
    }
    """
    supabase = current_app.config['SUPABASE']
    
    try:
        data = request.get_json()
        orden_numero = data.get("orden_numero")
        monto_abono = data.get("monto_abono")
        fecha_abono = data.get("fecha_abono")
        observacion = data.get("observacion", "")
        
        if not all([orden_numero, monto_abono, fecha_abono]):
            return jsonify({
                "success": False,
                "message": "Faltan datos requeridos"
            }), 400
        
        # Validar monto
        monto_abono = int(round(float(monto_abono)))
        if monto_abono <= 0:
            return jsonify({
                "success": False,
                "message": "El monto debe ser mayor a cero"
            }), 400
        
        # Obtener total de la orden
        orden = supabase.table("orden_de_pago").select(
            "costo_final_con_iva"
        ).eq("orden_numero", orden_numero).limit(1).execute()
        
        if not orden.data:
            return jsonify({
                "success": False,
                "message": "Orden no encontrada"
            }), 404
        
        total_pago = int(round(float(orden.data[0].get("costo_final_con_iva") or 0)))
        
        # Obtener suma de abonos existentes
        abonos = supabase.table("abonos_op").select("monto_abono").eq(
            "orden_numero", orden_numero
        ).execute()
        
        suma_abonos = sum(
            int(round(float(a.get("monto_abono") or 0))) 
            for a in (abonos.data or [])
        )
        
        # Validar que no exceda el total
        nueva_suma = suma_abonos + monto_abono
        if nueva_suma > total_pago:
            return jsonify({
                "success": False,
                "message": f"La suma de abonos ({nueva_suma}) supera el total ({total_pago})"
            }), 400
        
        # Insertar abono
        result = supabase.table("abonos_op").insert({
            "orden_numero": orden_numero,
            "monto_abono": monto_abono,
            "fecha_abono": fecha_abono,
            "observacion": observacion
        }).execute()
        
        # Si completa el total, asignar fecha de pago
        if nueva_suma == total_pago:
            supabase.table("fechas_de_pagos_op").upsert({
                "orden_numero": orden_numero,
                "fecha_pago": fecha_abono
            }, on_conflict=["orden_numero"]).execute()
        
        return jsonify({
            "success": True,
            "message": "Abono registrado exitosamente",
            "data": result.data[0] if result.data else None
        })
        
    except Exception as e:
        logger.error(f"Error en create_abono: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# ================================================================
# ENDPOINT - EDITAR ABONO
# ================================================================

@bp.route("/abono/<int:abono_id>", methods=["PUT"])
@token_required
def update_abono(current_user, abono_id):
    """Edita un abono existente"""
    supabase = current_app.config['SUPABASE']
    
    try:
        data = request.get_json()
        monto_abono = int(round(float(data.get("monto_abono") or 0)))
        fecha_abono = data.get("fecha_abono")
        observacion = data.get("observacion")
        
        if monto_abono <= 0:
            return jsonify({
                "success": False,
                "message": "El monto debe ser mayor a cero"
            }), 400
        
        # Obtener orden_numero del abono
        abono = supabase.table("abonos_op").select("orden_numero").eq(
            "id", abono_id
        ).limit(1).execute()
        
        if not abono.data:
            return jsonify({
                "success": False,
                "message": "Abono no encontrado"
            }), 404
        
        orden_numero = abono.data[0]["orden_numero"]
        
        # Obtener total de la orden
        orden = supabase.table("orden_de_pago").select(
            "costo_final_con_iva"
        ).eq("orden_numero", orden_numero).limit(1).execute()
        
        total_pago = int(round(float(orden.data[0].get("costo_final_con_iva") or 0)))
        
        # Suma de otros abonos (excluyendo el actual)
        otros_abonos = supabase.table("abonos_op").select("monto_abono").eq(
            "orden_numero", orden_numero
        ).neq("id", abono_id).execute()
        
        suma_otros = sum(
            int(round(float(a.get("monto_abono") or 0))) 
            for a in (otros_abonos.data or [])
        )
        
        # Validar nueva suma
        nueva_suma = suma_otros + monto_abono
        if nueva_suma > total_pago:
            return jsonify({
                "success": False,
                "message": f"La suma de abonos ({nueva_suma}) supera el total ({total_pago})"
            }), 400
        
        # Actualizar abono
        update_data = {"monto_abono": monto_abono}
        if fecha_abono:
            update_data["fecha_abono"] = fecha_abono
        if observacion is not None:
            update_data["observacion"] = observacion
        
        supabase.table("abonos_op").update(update_data).eq("id", abono_id).execute()
        
        # Actualizar fecha de pago si completa el total
        if nueva_suma == total_pago:
            supabase.table("fechas_de_pagos_op").upsert({
                "orden_numero": orden_numero,
                "fecha_pago": fecha_abono or date.today().isoformat()
            }, on_conflict=["orden_numero"]).execute()
        elif nueva_suma < total_pago:
            # Si no completa, eliminar fecha automática (solo si fue puesta por abonos)
            pass
        
        return jsonify({
            "success": True,
            "message": "Abono actualizado exitosamente"
        })
        
    except Exception as e:
        logger.error(f"Error en update_abono: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# ================================================================
# ENDPOINT - ELIMINAR ABONO
# ================================================================

@bp.route("/abono/<int:abono_id>", methods=["DELETE"])
@token_required
def delete_abono(current_user, abono_id):
    """Elimina un abono"""
    supabase = current_app.config['SUPABASE']
    
    try:
        # Obtener orden_numero del abono
        abono = supabase.table("abonos_op").select("orden_numero").eq(
            "id", abono_id
        ).limit(1).execute()
        
        if not abono.data:
            return jsonify({
                "success": False,
                "message": "Abono no encontrado"
            }), 404
        
        orden_numero = abono.data[0]["orden_numero"]
        
        # Eliminar abono
        supabase.table("abonos_op").delete().eq("id", abono_id).execute()
        
        # Verificar abonos restantes
        abonos_restantes = supabase.table("abonos_op").select("monto_abono").eq(
            "orden_numero", orden_numero
        ).execute()
        
        suma_restante = sum(
            int(round(float(a.get("monto_abono") or 0))) 
            for a in (abonos_restantes.data or [])
        )
        
        # Si no quedan abonos o no completan el total, eliminar fecha automática
        if suma_restante == 0:
            supabase.table("fechas_de_pagos_op").delete().eq(
                "orden_numero", orden_numero
            ).execute()
        else:
            # Verificar si completa el total
            orden = supabase.table("orden_de_pago").select(
                "costo_final_con_iva"
            ).eq("orden_numero", orden_numero).limit(1).execute()
            
            total_pago = int(round(float(orden.data[0].get("costo_final_con_iva") or 0)))
            
            if suma_restante < total_pago:
                supabase.table("fechas_de_pagos_op").delete().eq(
                    "orden_numero", orden_numero
                ).execute()
        
        return jsonify({
            "success": True,
            "message": "Abono eliminado exitosamente"
        })
        
    except Exception as e:
        logger.error(f"Error en delete_abono: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# ================================================================
# ENDPOINT - LISTAS PARA FILTROS
# ================================================================

@bp.route("/filters", methods=["GET"])
@token_required
def get_filters(current_user):
    """Obtiene listas para los filtros (proveedores, proyectos)"""
    try:
        proveedores = get_cached_proveedores()
        proyectos = get_cached_proyectos()
        
        return jsonify({
            "success": True,
            "data": {
                "proveedores": [
                    {"id": p["id"], "nombre": p["nombre"]} 
                    for p in proveedores
                ],
                "proyectos": [
                    {"id": p["id"], "nombre": p["proyecto"]} 
                    for p in proyectos
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"Error en get_filters: {e}")
        return jsonify({"success": False, "message": str(e)}), 500