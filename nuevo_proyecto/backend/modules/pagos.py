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
    """
    Calcular estado del pago:
    - pagado: tiene fecha_pago (preferible) O saldo = 0
    - abono: tiene abonos parciales (saldo > 0)
    - pendiente: sin fecha_pago y sin abonos (o con saldo > 0)
    """
    saldo = max(0, total_pago - (total_abonado or 0))

    # Caso 1: Si hay abonos parciales y queda saldo -> ABONO (priorizar abonos)
    if (total_abonado or 0) > 0 and saldo > 0:
        return "abono"

    # Caso 2: Si hay fecha de pago o el saldo es cero -> PAGADO
    if fecha_pago or saldo <= 0:
        return "pagado"

    # Caso 3: Sin fecha, sin abonos, con saldo > 0 -> PENDIENTE
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
        estado_filtro = request.args.get('estado', '').strip()  # Renombrado para evitar conflicto
        # Normalizar posibles etiquetas que envía el front (p. ej. "Con Abonos")
        if estado_filtro:
            ef = estado_filtro.lower().strip()
            # Mapear etiquetas de UI a códigos internos
            if ef in ("con abonos", "con_abonos", "con-abonos", "conabonos", "con abono", "con_abono"):
                estado_filtro = "abono"
            elif ef in ("con pagos", "pagadas", "pagado", "pagados", "pagado(s)"):
                estado_filtro = "pagado"
            elif ef in ("pendiente", "pendientes"):
                estado_filtro = "pendiente"
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
                    "total_pago": 0,
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
            # Usar enteros redondeados para evitar imprecisiones con floats (pesos/cop)
            try:
                monto = int(round(float(r.get("costo_final_con_iva") or 0)))
            except Exception:
                monto = 0
            pagos_dict[num]["total_pago"] += monto
        
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
                        try:
                            monto_ab = int(round(float(ab.get("monto_abono") or 0)))
                        except Exception:
                            monto_ab = 0
                        abonos_map[num] = abonos_map.get(num, 0) + monto_ab
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
                fecha_pago_bd = fecha_map.get(num)  # Fecha original de BD
                # Asegurarse de trabajar con enteros para total y abonos
                total_abonado = int(abonos_map.get(num, 0))
                total_pago = int(pago["total_pago"])

                # Calcular saldo (enteros)
                saldo = max(0, total_pago - total_abonado)
                
                # Calcular ESTADO primero (usa fecha_pago_bd original)
                estado = calcular_estado_pago(fecha_pago_bd, total_abonado, total_pago)
                
                # Determinar qué fecha_pago MOSTRAR al usuario:
                # - Si tiene fecha Y NO tiene abonos: mostrar (pago directo completo)
                # - Si tiene abonos Y saldo <= 0: mostrar (pagado con abonos completos)
                # - Si tiene abonos Y saldo > 0: NO mostrar (pago parcial)
                if fecha_pago_bd and total_abonado == 0:
                    # Pago directo sin abonos
                    fecha_pago_mostrar = fecha_pago_bd
                elif total_abonado > 0 and saldo <= 0:
                    # Pagado completamente con abonos
                    fecha_pago_mostrar = fecha_pago_bd or date.today().isoformat()
                else:
                    # Pendiente o con abonos parciales - NO mostrar fecha
                    fecha_pago_mostrar = None
                
                pago["fecha_pago"] = fecha_pago_mostrar
                pago["total_abonado"] = total_abonado
                pago["saldo_pendiente"] = saldo
                pago["rut_proveedor"] = rut_map.get(pago.get("proveedor"), "-")
                pago["proyecto_nombre"] = proyecto_map.get(pago["proyecto"], f"Proyecto {pago['proyecto']}")
                pago["estado"] = estado
        
        # Filtro de estado (post-procesamiento)
        if estado_filtro:
            pagos_list = [p for p in pagos_list if p["estado"] == estado_filtro]
        
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
    Obtiene estadísticas generales de pagos con retry logic.
    Aplica los mismos filtros que list_pagos.
    """
    supabase = current_app.config['SUPABASE']
    
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5
    
    for intento in range(MAX_RETRIES):
        try:
            # Filtros (mismos que list_pagos)
            proveedor = request.args.get('proveedor', '').strip()
            proyecto_id = request.args.get('proyecto', '').strip()
            fecha_desde = request.args.get('fecha_desde', '').strip()
            fecha_hasta = request.args.get('fecha_hasta', '').strip()
            
            # Obtener todas las filas de `orden_de_pago` aplicando los mismos filtros
            # que usa la vista detallada. Para evitar límites de Supabase, hacemos
            # paginado por lotes (batching) igual que el sistema antiguo.
            page_size = 1000
            offset = 0
            all_rows = []

            while True:
                q = supabase.table("orden_de_pago").select(
                    "orden_numero, costo_final_con_iva, proyecto"
                ).order("orden_numero", desc=True).range(offset, offset + page_size - 1)

                if proveedor:
                    q = q.ilike("proveedor_nombre", f"%{proveedor}%")
                if proyecto_id:
                    try:
                        q = q.eq("proyecto", int(proyecto_id))
                    except ValueError:
                        pass
                if fecha_desde:
                    q = q.gte("fecha", fecha_desde)
                if fecha_hasta:
                    q = q.lte("fecha", fecha_hasta)

                res = q.execute()
                batch = res.data or []
                all_rows.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size
            
            # Agrupar por orden_numero
            pagos_dict = {}
            for r in all_rows:
                num = r["orden_numero"]
                if num not in pagos_dict:
                    pagos_dict[num] = {
                        "orden_numero": num,
                        "total_pago": 0,
                        "proyecto": r["proyecto"]
                    }
                try:
                    monto = int(round(float(r.get("costo_final_con_iva") or 0)))
                except Exception:
                    monto = 0
                pagos_dict[num]["total_pago"] += monto
            
            orden_numeros = list(pagos_dict.keys())
            
            # Obtener fechas de pago y abonos
            fecha_map = {}
            abonos_map = {}

            # Para evitar problemas de tipos y asegurar coincidencia con la vista
            # antigua, traemos las filas de `fechas_de_pagos_op` por lotes y construimos
            # un mapa con claves como strings y como ints.
            try:
                page_size = 1000
                off = 0
                fechas_data = []
                while True:
                    batch = supabase.table("fechas_de_pagos_op").select("orden_numero, fecha_pago").range(off, off + page_size - 1).execute().data or []
                    if not batch:
                        break
                    fechas_data.extend(batch)
                    off += page_size
                # Construir mapa con claves string e int
                for row in fechas_data:
                    k = row.get("orden_numero")
                    v = row.get("fecha_pago")
                    if k is None:
                        continue
                    fecha_map[str(k)] = v
                    try:
                        fecha_map[int(k)] = v
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Error obteniendo fechas en batches: {e}")

            # Abonos: traer todos los abonos y acumular por orden
            try:
                abonos_data = supabase.table("abonos_op").select("orden_numero, monto_abono").execute().data or []
                for ab in abonos_data:
                    num = ab.get("orden_numero")
                    try:
                        monto = int(round(float(ab.get("monto_abono") or 0)))
                    except Exception:
                        monto = 0
                    if num is None:
                        continue
                    # Acumular tanto con la clave original como con la clave int (si corresponde)
                    abonos_map[num] = abonos_map.get(num, 0) + monto
                    try:
                        abonos_map[int(num)] = abonos_map.get(int(num), 0) + monto
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Error obteniendo abonos: {e}")
            
            # Calcular métricas siguiendo la nueva regla de negocio:
            # - Se parte de los valores únicos de `orden_numero` en `orden_de_pago` (ya está en pagos_dict)
            # - Si una orden aparece en `fechas_de_pagos_op` la consideramos pagada y NO la includimos
            #   en el cálculo de "total_pendiente".
            total_ordenes = len(pagos_dict)

            # Conjunto de órdenes con fecha de pago (pagadas)
            ordenes_con_fecha = set(fecha_map.keys())

            # Contadores
            pagadas = 0
            pendientes = 0

            total_pendiente = 0.0
            saldo_por_proyecto = {}

            # Proyectos
            proyectos = get_cached_proyectos()
            proyecto_map = {p["id"]: p["proyecto"] for p in proyectos}

            # Recorremos las órdenes únicas y aplicamos la misma lógica que el sistema antiguo:
            # - Si una orden tiene `fecha_pago` en la tabla `fechas_de_pagos_op` → saldo = 0
            # - Si no tiene fecha, saldo = max(0, total_pago - total_abonado)
            # - `total_pendiente` es la suma de esos saldos
            for num, pago in pagos_dict.items():
                total_abonado = abonos_map.get(num, 0)
                total_pago = pago["total_pago"]
                fecha_pago = fecha_map.get(num)

                # Calcular saldo: si hay fecha de pago, consideramos saldo 0 (pago directo o completado)
                saldo = 0 if fecha_pago else max(0, total_pago - total_abonado)

                # Mantener consistencia usando la función de estado
                estado = calcular_estado_pago(fecha_pago, total_abonado, total_pago)

                if estado == "pagado":
                    pagadas += 1
                else:
                    pendientes += 1
                    total_pendiente += saldo
                    proyecto_nombre = proyecto_map.get(pago.get("proyecto"), str(pago.get("proyecto")))
                    saldo_por_proyecto[proyecto_nombre] = saldo_por_proyecto.get(proyecto_nombre, 0) + saldo

            # Log de depuración para diagnosticar valores inesperados
            logger.debug(f"get_stats: filas_consultadas={len(all_rows)}, ordenes_unicas={len(pagos_dict)}, ordenes_con_fecha={len(ordenes_con_fecha)}")

            # Filtrar proyectos con saldo significativo (> 1 para evitar ruidos)
            saldo_por_proyecto = {k: v for k, v in saldo_por_proyecto.items() if v > 1}

            logger.info(f"📊 Stats calculadas exitosamente: pendientes={pendientes}, total_pendiente={total_pendiente}")

            # Si se solicita debug, devolver datos adicionales para diagnóstico
            if request.args.get('debug') == '1':
                muestra_ordenes = list(pagos_dict.keys())[:20]
                muestra_fechas = {k: fecha_map.get(k) for k in muestra_ordenes}
                muestra_abonos = {k: abonos_map.get(k, 0) for k in muestra_ordenes}
                return jsonify({
                    "success": True,
                    "data": {
                        "total_ordenes": total_ordenes,
                        "pagadas": pagadas,
                        "pendientes": pendientes,
                        "total_pendiente": total_pendiente,
                        "saldo_por_proyecto": saldo_por_proyecto,
                        "debug": {
                            "filas_consultadas": len(all_rows),
                            "ordenes_unicas_consideradas": len(pagos_dict),
                            "ordenes_con_fecha_count": len(fecha_map),
                            "ordenes_con_abonos_count": len(abonos_map),
                            "muestra_ordenes": muestra_ordenes,
                            "muestra_fechas": muestra_fechas,
                            "muestra_abonos": muestra_abonos
                        }
                    }
                })

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
            if intento < MAX_RETRIES - 1:
                logger.warning(f"Intento {intento + 1} falló en get_stats: {e}. Reintentando...")
                import time
                time.sleep(RETRY_DELAY)
                continue
            else:
                logger.error(f"Error en get_stats después de {MAX_RETRIES} intentos: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({"success": False, "message": "Error interno del servidor"}), 500
    
    # Si llegamos aquí es porque todos los reintentos fallaron
    return jsonify({"success": False, "message": "Error interno del servidor"}), 500

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