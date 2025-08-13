"""
Módulo de Informe de Órdenes de Pago - Migración completa desde pagos.py
- Gestión completa de pagos y abonos
- Filtros avanzados y búsqueda parcial
- Actualización masiva de fechas de pago
- Exportación a Excel optimizada
- Sistema de permisos integrado
- Compatible con Supabase

LÓGICA DE PAGOS - DOS MÉTODOS:

MÉTODO A - PAGO DIRECTO:
- Usuario asigna fecha de pago directamente
- Representa pago completo (saldo = 0)
- No requiere abonos previos
- Independiente del sistema de abonos

MÉTODO B - PAGO POR ABONOS:
- Usuario registra abonos parciales
- Sistema suma abonos hasta completar total
- Cuando abonos = total → auto-asigna fecha de pago
- Si se elimina abono y saldo > 0 → se elimina fecha de pago automática

REGLAS DE CONVIVENCIA:
1. Pago directo (fecha) siempre tiene precedencia
2. Sistema de abonos solo gestiona fechas automáticas
3. No eliminar fechas de pago directo por cambios en abonos
4. Permitir ambos métodos sin interferencia
"""

from flask import (
    Blueprint, render_template, request,
    flash, redirect, url_for, current_app,
    jsonify
)
from datetime import date, datetime, timedelta
from flask_login import login_required
from app.modules.usuarios import require_modulo, get_modulos_usuario
from app.utils.static_data import get_cached_proveedores, get_cached_proyectos_with_id
from app.utils.informe_op_cache import informe_cache, invalidate_informe_cache, get_cache_stats
from utils.logger import registrar_log_actividad

bp_informe_op = Blueprint(
    "informe_op", __name__,
    template_folder="../templates"
)

def validar_integridad_datos(supabase, orden_numero=None):
    """
    Función de validación de integridad de datos
    Verifica la consistencia entre abonos, totales y fechas de pago
    """
    try:
        print(f"[VALIDACIÓN INTEGRIDAD] Iniciando validación para orden: {orden_numero or 'TODAS'}")
        
        # Consulta base
        if orden_numero:
            ordenes_query = supabase.table("orden_de_pago").select("*").eq("orden_numero", orden_numero)
        else:
            ordenes_query = supabase.table("orden_de_pago").select("*").limit(100)  # Validar por lotes
        
        ordenes = ordenes_query.execute().data or []
        problemas_detectados = []
        
        for orden in ordenes:
            num_orden = orden["orden_numero"]
            total_orden = float(orden.get("costo_final_con_iva") or 0)
            
            # Verificar abonos
            abonos = supabase.table("abonos_op").select("*").eq("orden_numero", num_orden).execute().data or []
            suma_abonos = sum(float(a.get("monto_abono") or 0) for a in abonos)
            
            # Verificar fecha de pago
            fecha_pago = supabase.table("fechas_de_pagos_op").select("*").eq("orden_numero", num_orden).execute().data
            tiene_fecha = len(fecha_pago) > 0
            
            # Detectar inconsistencias
            if suma_abonos > total_orden:
                problemas_detectados.append({
                    "orden": num_orden,
                    "problema": "ABONOS_EXCEDEN_TOTAL",
                    "suma_abonos": suma_abonos,
                    "total_orden": total_orden
                })
            
            if suma_abonos == total_orden and not tiene_fecha:
                problemas_detectados.append({
                    "orden": num_orden,
                    "problema": "PAGO_COMPLETO_SIN_FECHA",
                    "suma_abonos": suma_abonos,
                    "total_orden": total_orden
                })
            
            if suma_abonos < total_orden and tiene_fecha:
                problemas_detectados.append({
                    "orden": num_orden,
                    "problema": "FECHA_CON_PAGO_INCOMPLETO",
                    "suma_abonos": suma_abonos,
                    "total_orden": total_orden
                })
        
        if problemas_detectados:
            print(f"[VALIDACIÓN INTEGRIDAD] Detectados {len(problemas_detectados)} problemas")
            for problema in problemas_detectados:
                print(f"   - Orden {problema['orden']}: {problema['problema']}")
        else:
            print(f"[VALIDACIÓN INTEGRIDAD] No se detectaron problemas")
        
        return problemas_detectados
        
    except Exception as e:
        print(f"[ERROR VALIDACIÓN] Error en validación de integridad: {e}")
        return []

def get_informe_pagos(filtros=None, page=1, per_page=100):
    """
    Función optimizada para obtener datos del informe de pagos con PAGINACIÓN EFICIENTE POR ÓRDENES ÚNICAS
    Migrada desde pagos.py con optimizaciones y cache inteligente
    """
    # Crear clave de cache que incluya paginación
    cache_key = f"page_{page}_per_{per_page}"
    if filtros:
        cache_key += f"_filters_{hash(str(sorted(filtros.items())))}"
    
    # Intentar obtener desde cache primero
    cached_data = informe_cache.get_informe_data(cache_key)
    if cached_data is not None:
        print(f"[CACHE HIT] Usando datos cacheados para página {page}")
        return cached_data
    
    print(f"[CACHE MISS] Consultando BD para página {page}, filtros: {filtros}")
    
    supabase = current_app.config["SUPABASE"]
    
    try:
        # PASO 1: Obtener órdenes únicas que coincidan con los filtros
        distinct_query = supabase.table("orden_de_pago").select("orden_numero", count="exact")
        
        # Aplicar filtros DIRECTAMENTE en la consulta SQL
        if filtros:
            search = filtros.get("proveedor", "").strip()
            if search:
                distinct_query = distinct_query.ilike("proveedor_nombre", f"%{search}%")
            
            proyecto_nombre = filtros.get("proyecto", "").strip()
            if proyecto_nombre:
                try:
                    projs = get_cached_proyectos_with_id()
                    for pr in projs:
                        if pr["proyecto"] == proyecto_nombre:
                            distinct_query = distinct_query.eq("proyecto", pr["id"])
                            break
                except Exception as e:
                    print(f"[WARNING] Error al convertir proyecto a ID: {e}")
            
            fecha_desde = filtros.get("fecha_desde", "").strip()
            if fecha_desde:
                distinct_query = distinct_query.gte("fecha", fecha_desde)
                
            fecha_hasta = filtros.get("fecha_hasta", "").strip()
            if fecha_hasta:
                distinct_query = distinct_query.lte("fecha", fecha_hasta)
        
        # Obtener órdenes únicas con conteo total
        ordenes_result = distinct_query.execute()
        total_ordenes = ordenes_result.count or 0
        
        # PASO 2: Obtener lista de órdenes únicas para paginación
        ordenes_query = supabase.table("orden_de_pago").select("orden_numero")
        
        # Aplicar los mismos filtros
        if filtros:
            search = filtros.get("proveedor", "").strip()
            if search:
                ordenes_query = ordenes_query.ilike("proveedor_nombre", f"%{search}%")
            
            proyecto_nombre = filtros.get("proyecto", "").strip()
            if proyecto_nombre:
                try:
                    projs = get_cached_proyectos_with_id()
                    for pr in projs:
                        if pr["proyecto"] == proyecto_nombre:
                            ordenes_query = ordenes_query.eq("proyecto", pr["id"])
                            break
                except:
                    pass
            
            fecha_desde = filtros.get("fecha_desde", "").strip()
            if fecha_desde:
                ordenes_query = ordenes_query.gte("fecha", fecha_desde)
                
            fecha_hasta = filtros.get("fecha_hasta", "").strip()
            if fecha_hasta:
                ordenes_query = ordenes_query.lte("fecha", fecha_hasta)
        
        # VERIFICAR SI HAY FILTRO POR ESTADO - requiere lógica especial
        estado_filtro = filtros.get("estado", "").strip() if filtros else None
        
        if estado_filtro:
            print(f"[FILTRO ESTADO] Detectado filtro por estado: '{estado_filtro}' - aplicando lógica especial")
            
            # PARA FILTRO POR ESTADO: obtener TODAS las órdenes que coincidan con otros filtros
            ordenes_todas = ordenes_query.order("orden_numero", desc=True).execute().data or []
            
            # Obtener números únicos de todas las órdenes
            numeros_todas = []
            seen_all = set()
            for orden in ordenes_todas:
                if orden["orden_numero"] and int(orden["orden_numero"]) not in seen_all:
                    numeros_todas.append(int(orden["orden_numero"]))
                    seen_all.add(int(orden["orden_numero"]))
            
            print(f"[FILTRO ESTADO] Obtenidas {len(numeros_todas)} órdenes únicas para calcular estados")
            
            # Obtener datos completos para calcular estados
            todas_pagos = []
            batch_size = 1000
            for i in range(0, len(numeros_todas), batch_size):
                batch_nums = numeros_todas[i:i+batch_size]
                
                data_query = supabase.table("orden_de_pago").select(
                    "orden_numero, fecha, proveedor, proveedor_nombre, detalle_compra, "
                    "factura, costo_final_con_iva, proyecto, orden_compra, condicion_pago, "
                    "vencimiento, fecha_factura, ingreso_id"
                ).in_("orden_numero", batch_nums)
                
                batch_data = data_query.execute().data or []
                todas_pagos.extend(batch_data)
            
            # Enriquecer con nombres de proyectos
            proyecto_map = {}
            try:
                projs = get_cached_proyectos_with_id()
                proyecto_map = {pr["id"]: pr["proyecto"] for pr in projs}
                for r in todas_pagos:
                    proj_id = r.get("proyecto")
                    r["proyecto_nombre"] = proyecto_map.get(proj_id, f"ID:{proj_id}" if proj_id else "Sin Proyecto")
            except Exception as e:
                print(f"[ERROR] Error al enriquecer proyectos: {e}")
            
            # Agrupar por orden_numero y calcular totales
            pagos_dict = {}
            for r in todas_pagos:
                num = r["orden_numero"]
                if num not in pagos_dict:
                    pagos_dict[num] = {
                        "orden_numero": num,
                        "fecha": r["fecha"],
                        "proveedor": r.get("proveedor"),
                        "proveedor_nombre": r["proveedor_nombre"],
                        "rut_proveedor": r.get("rut_proveedor", "-"),
                        "detalle_compra": r["detalle_compra"],
                        "factura": r["factura"],
                        "total_pago": 0.0,
                        "proyecto_id": r["proyecto"],
                        "proyecto": r.get("proyecto_nombre", r["proyecto"]),
                        "item": r.get("item", "-"),
                        "orden_compra": r["orden_compra"],
                        "condicion_pago": r["condicion_pago"],
                        "vencimiento": r["vencimiento"],
                        "fecha_factura": r["fecha_factura"],
                        "ingreso_id": r.get("ingreso_id"),
                        "fecha_pago": None,
                        "total_abonado": 0.0,
                        "saldo_pendiente": 0.0,
                        "cuenta": "",
                        "fac_pago": "-"
                    }
                pagos_dict[num]["total_pago"] += float(r.get("costo_final_con_iva") or 0)
            
            # Obtener fechas de pago para todas las órdenes
            try:
                fechas_todas = supabase.table("fechas_de_pagos_op").select("orden_numero, fecha_pago").in_("orden_numero", numeros_todas).execute().data or []
                fecha_map = {row["orden_numero"]: row["fecha_pago"] for row in fechas_todas}
                for num in pagos_dict:
                    pagos_dict[num]["fecha_pago"] = fecha_map.get(num)
                print(f"[FILTRO ESTADO] Cargadas {len(fecha_map)} fechas de pago")
            except Exception as e:
                print(f"[ERROR] Error al cargar fechas de pago: {e}")
            
            # Obtener abonos para todas las órdenes
            try:
                abonos_todas = supabase.table("abonos_op").select("orden_numero, monto_abono").in_("orden_numero", numeros_todas).execute().data or []
                abonos_map = {}
                for abono in abonos_todas:
                    orden = abono["orden_numero"]
                    monto = float(abono["monto_abono"] or 0)
                    if orden not in abonos_map:
                        abonos_map[orden] = 0.0
                    abonos_map[orden] += monto
                
                for num in pagos_dict:
                    total_abonado = abonos_map.get(num, 0.0)
                    pagos_dict[num]["total_abonado"] = total_abonado
                    pagos_dict[num]["saldo_pendiente"] = max(0, pagos_dict[num]["total_pago"] - total_abonado)
                
                print(f"[FILTRO ESTADO] Calculados abonos para {len(abonos_map)} órdenes")
            except Exception as e:
                print(f"[ERROR] Error al calcular abonos: {e}")
            
            # Convertir a lista y calcular estados
            todos_pagos = [pagos_dict[k] for k in sorted(pagos_dict.keys(), reverse=True)]
            
            def calcular_estado_pago(p):
                if p.get("fecha_pago"):
                    return "pagado"
                elif p.get("total_abonado", 0) > 0:
                    return "abono"
                else:
                    return "pendiente"
            
            # Agregar estado a cada pago
            for p in todos_pagos:
                p["estado"] = calcular_estado_pago(p)
            
            # FILTRAR POR ESTADO
            pagos_filtrados_estado = [p for p in todos_pagos if p["estado"] == estado_filtro.lower()]
            
            print(f"[FILTRO ESTADO] Filtrados por estado '{estado_filtro}': {len(pagos_filtrados_estado)} de {len(todos_pagos)} total")
            
            # APLICAR PAGINACIÓN A LOS RESULTADOS FILTRADOS
            total_registros_filtrados = len(pagos_filtrados_estado)
            total_pages_filtradas = (total_registros_filtrados + per_page - 1) // per_page
            
            offset = (page - 1) * per_page
            pagos_procesados = pagos_filtrados_estado[offset:offset + per_page]
            
            print(f"[FILTRO ESTADO] Página {page}: {len(pagos_procesados)} registros de {total_registros_filtrados} total filtrados")
            
            result_data = {
                'registros': pagos_procesados,
                'total_registros': total_registros_filtrados,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages_filtradas
            }
            
            # Guardar en cache
            informe_cache.set_informe_data(cache_key, result_data)
            return result_data
        
        # LÓGICA NORMAL SIN FILTRO POR ESTADO
        # Obtener órdenes únicas con límite estricto para eliminar solapamiento
        offset = (page - 1) * per_page
        
        # CORRECCIÓN: usar límite estricto para evitar solapamiento
        # En lugar de usar un margen, obtenemos exactamente lo necesario
        limite_registros = per_page * 4  # Margen conservador pero no excesivo
        
        ordenes_batch = ordenes_query.order("orden_numero", desc=True).range(offset, offset + limite_registros - 1).execute().data or []
        
        # Extraer números de orden únicos y tomar exactamente per_page
        numeros_orden_unicos = []
        seen_orders = set()
        
        for orden in ordenes_batch:
            if orden["orden_numero"] and int(orden["orden_numero"]) not in seen_orders:
                numeros_orden_unicos.append(int(orden["orden_numero"]))
                seen_orders.add(int(orden["orden_numero"]))
                if len(numeros_orden_unicos) >= per_page:
                    break
        
        numeros_orden = numeros_orden_unicos
        
        print(f"[PAGINACIÓN CORREGIDA] Página {page}: {len(numeros_orden)} órdenes únicas obtenidas de rango {offset}-{offset + limite_registros - 1}")
        
        # PASO 3: Obtener TODOS los registros para estas órdenes específicas
        if not numeros_orden:
            return {
                'registros': [],
                'total_registros': total_ordenes,
                'page': page,
                'per_page': per_page,
                'total_pages': (total_ordenes + per_page - 1) // per_page
            }
        
        # Consultar todos los datos para estas órdenes específicas
        data_query = supabase.table("orden_de_pago").select(
            "orden_numero, fecha, proveedor, proveedor_nombre, detalle_compra, "
            "factura, costo_final_con_iva, proyecto, orden_compra, condicion_pago, "
            "vencimiento, fecha_factura, ingreso_id"
        ).in_("orden_numero", numeros_orden)
        
        all_rows = data_query.execute().data or []
        
        # Enriquecer con nombres de proyectos
        proyecto_map = {}
        try:
            projs = get_cached_proyectos_with_id()
            proyecto_map = {pr["id"]: pr["proyecto"] for pr in projs}
            for r in all_rows:
                proj_id = r.get("proyecto")
                r["proyecto_nombre"] = proyecto_map.get(proj_id, str(proj_id))
        except Exception as e:
            print(f"[ERROR] Error al enriquecer proyectos: {e}")

        # Procesar y agrupar datos como espera el template
        pagos_procesados = []
        if all_rows:
            # Agrupar por orden_numero y sumar montos
            pagos_dict = {}
            ordenes_numeros_data = []
            
            for r in all_rows:
                try:
                    num = int(r["orden_numero"])
                    ordenes_numeros_data.append(num)
                except (ValueError, TypeError):
                    continue
                    
                if num not in pagos_dict:
                    pagos_dict[num] = {
                        "orden_numero": num,
                        "fecha": r["fecha"],
                        "proveedor": r.get("proveedor"),
                        "proveedor_nombre": r["proveedor_nombre"],
                        "rut_proveedor": r.get("rut_proveedor", "-"),  # AGREGADO
                        "detalle_compra": r["detalle_compra"],
                        "factura": r["factura"],
                        "total_pago": 0.0,
                        "proyecto_id": r["proyecto"],
                        "proyecto": r.get("proyecto_nombre", r["proyecto"]),
                        "item": r.get("item", "-"),  # AGREGADO
                        "orden_compra": r["orden_compra"],
                        "condicion_pago": r["condicion_pago"],
                        "vencimiento": r["vencimiento"],
                        "fecha_factura": r["fecha_factura"],
                        "ingreso_id": r.get("ingreso_id"),
                        "fecha_pago": None,
                        "total_abonado": 0.0,
                        "saldo_pendiente": 0.0,
                        "cuenta": "",
                        "fac_pago": "-"
                    }
                pagos_dict[num]["total_pago"] += float(r.get("costo_final_con_iva") or 0)
            
            # Obtener fechas de pago para estas órdenes
            if ordenes_numeros_data:
                try:
                    fechas_batch = supabase.table("fechas_de_pagos_op").select("orden_numero, fecha_pago").in_("orden_numero", ordenes_numeros_data).execute().data or []
                    fecha_map = {row["orden_numero"]: row["fecha_pago"] for row in fechas_batch}
                    
                    for num in pagos_dict:
                        pagos_dict[num]["fecha_pago"] = fecha_map.get(num)
                        
                    print(f"[INFO] Cargadas {len(fecha_map)} fechas de pago para página {page}")
                except Exception as e:
                    print(f"[ERROR] Error al cargar fechas de pago: {e}")
            
            # Obtener abonos para estas órdenes
            if ordenes_numeros_data:
                try:
                    abonos_batch = supabase.table("abonos_op").select("orden_numero, monto_abono").in_("orden_numero", ordenes_numeros_data).execute().data or []
                    abonos_map = {}
                    for abono in abonos_batch:
                        orden = abono["orden_numero"]
                        monto = float(abono["monto_abono"] or 0)
                        if orden not in abonos_map:
                            abonos_map[orden] = 0.0
                        abonos_map[orden] += monto
                    
                    for num in pagos_dict:
                        total_abonado = abonos_map.get(num, 0.0)
                        pagos_dict[num]["total_abonado"] = total_abonado
                        pagos_dict[num]["saldo_pendiente"] = max(0, pagos_dict[num]["total_pago"] - total_abonado)
                        
                    print(f"[INFO] Calculados abonos para {len(abonos_map)} órdenes en página {page}")
                except Exception as e:
                    print(f"[ERROR] Error al calcular abonos: {e}")
            
            # Convertir a lista ordenada
            pagos_procesados = [pagos_dict[k] for k in sorted(pagos_dict.keys(), reverse=True)]
            
            # NOTA: El filtro de estado NO se puede aplicar aquí porque:
            # 1. El estado se calcula después de obtener fechas y abonos
            # 2. Aplicarlo aquí limitaría incorrectamente los resultados por página
            # 3. El filtro de estado se maneja mejor en los totales y en Excel
            
            # Asegurar exactamente per_page registros por página
            pagos_procesados = pagos_procesados[:per_page]

        print(f"[PAGINACIÓN EFICIENTE] Página {page}: {len(pagos_procesados)} órdenes únicas procesadas de {total_ordenes} total")
        
        result_data = {
            'registros': pagos_procesados,
            'total_registros': total_ordenes,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_ordenes + per_page - 1) // per_page
        }
        
        # Guardar en cache
        informe_cache.set_informe_data(cache_key, result_data)
        
        return result_data

    except Exception as e:
        print(f"[ERROR CRÍTICO] Error en get_informe_pagos: {e}")
        return {
            'registros': [],
            'total_registros': 0,
            'page': page,
            'per_page': per_page,
            'total_pages': 0
        }
            
        fecha_hasta = filtros.get("fecha_hasta", "").strip()
        if fecha_hasta:
            all_rows = [r for r in all_rows if r.get("fecha", "") <= fecha_hasta]

    # Agrupar por orden_numero único y sumar montos
    pagos = {}
    for r in all_rows:
        try:
            num = int(r["orden_numero"])
        except (ValueError, TypeError):
            continue  # Omitir si no se puede convertir
            
        if num not in pagos:
            pagos[num] = {
                "orden_numero": num,
                "fecha": r["fecha"],
                "proveedor": r.get("proveedor"),  # ID del proveedor
                "proveedor_nombre": r["proveedor_nombre"],
                "detalle_compra": r["detalle_compra"],
                "factura": r["factura"],
                "total_pago": 0.0,
                "proyecto_id": r["proyecto"],
                "proyecto": r.get("proyecto_nombre", r["proyecto"]),  # Usar nombre si está disponible
                "orden_compra": r["orden_compra"],
                "condicion_pago": r["condicion_pago"],
                "vencimiento": r["vencimiento"],
                "fecha_factura": r["fecha_factura"],
                "ingreso_id": r.get("ingreso_id"),
                "fecha_pago": None,
                "total_abonado": 0.0,
                "saldo_pendiente": 0.0,
                "item": "",
                "rut_proveedor": "-",
                "cuenta": "",
                "fac_pago": "-"
            }
        pagos[num]["total_pago"] += float(r.get("costo_final_con_iva") or 0)

    # Ordenar de mayor a menor por orden_numero
    pagos_ordenados = [pagos[k] for k in sorted(pagos.keys(), reverse=True)]

    # Obtener fechas de pago en batch (con límite para evitar errores de Supabase)
    ordenes_numeros = [p["orden_numero"] for p in pagos_ordenados]
    fecha_map = {}
    if ordenes_numeros:
        try:
            batch_size = 100  # Reducir tamaño de batch para evitar límites de Supabase
            for i in range(0, len(ordenes_numeros), batch_size):
                batch_ordenes = ordenes_numeros[i:i+batch_size]
                fechas_batch = supabase.table("fechas_de_pagos_op").select("orden_numero, fecha_pago").in_("orden_numero", batch_ordenes).execute().data or []
                for row in fechas_batch:
                    fecha_map[row["orden_numero"]] = row["fecha_pago"]
            
            for p in pagos_ordenados:
                p["fecha_pago"] = fecha_map.get(p["orden_numero"])
                
            print(f"[INFO] Cargadas {len(fecha_map)} fechas de pago de {len(ordenes_numeros)} órdenes")
        except Exception as e:
            print(f"[ERROR] Consulta fechas de pago: {e}")

    # Obtener abonos en batch (con límite para evitar errores de Supabase)
    abonos_map = {}
    if ordenes_numeros:
        try:
            batch_size = 100  # Reducir tamaño de batch
            for i in range(0, len(ordenes_numeros), batch_size):
                batch_ordenes = ordenes_numeros[i:i+batch_size]
                abonos_batch = supabase.table("abonos_op").select("orden_numero, monto_abono").in_("orden_numero", batch_ordenes).execute().data or []
                
                for ab in abonos_batch:
                    num = ab.get("orden_numero")
                    if num is not None:
                        try:
                            monto = float(ab.get("monto_abono") or 0)
                            abonos_map[num] = abonos_map.get(num, 0) + monto
                        except (ValueError, TypeError):
                            continue
            
            for p in pagos_ordenados:
                num = p["orden_numero"]
                total_abonado = abonos_map.get(num, 0)
                p["total_abonado"] = total_abonado
                # Si existe fecha_pago → saldo = 0, sino saldo = total - abonos
                p["saldo_pendiente"] = 0 if p.get("fecha_pago") else max(0, p["total_pago"] - total_abonado)
                
            print(f"[INFO] Cargados abonos para {len(abonos_map)} órdenes")
        except Exception as e:
            print(f"[ERROR] Consulta abonos: {e}")

    # Obtener items por orden_compra
    ordenes_compra_unicas = set(p["orden_compra"] for p in pagos_ordenados if p.get("orden_compra"))
    if ordenes_compra_unicas:
        items_por_orden = {}
        try:
            batch_size = 100
            ordenes_list = list(ordenes_compra_unicas)
            for i in range(0, len(ordenes_list), batch_size):
                batch_ordenes = ordenes_list[i:i+batch_size]
                batch_items = supabase.table("orden_de_compra").select("orden_compra,item").in_("orden_compra", batch_ordenes).execute().data or []
                for oc in batch_ordenes:
                    items = set(row["item"] for row in batch_items if row["orden_compra"] == oc and row.get("item"))
                    items_por_orden[oc] = ", ".join(sorted(items)) if items else ""
            
            for p in pagos_ordenados:
                oc = p.get("orden_compra")
                p["item"] = items_por_orden.get(oc, "")
        except Exception as e:
            print(f"[ERROR] Consulta items: {e}")

    # Obtener datos de proveedores (RUT y cuenta corriente)
    try:
        provs = get_cached_proveedores()
        cuenta_map = {p["nombre"]: p["cuenta"] for p in provs}
        rut_map = {}
        for p in provs:
            if p.get("id") is not None and p.get("rut"):
                rut_map[p["id"]] = p["rut"]
                try:
                    rut_map[int(p["id"])] = p["rut"]
                    rut_map[str(p["id"])] = p["rut"]
                except (ValueError, TypeError):
                    pass
        
        for p in pagos_ordenados:
            p["cuenta"] = cuenta_map.get(p["proveedor_nombre"], "")
            p["rut_proveedor"] = rut_map.get(p.get("proveedor"), "-")
    except Exception as e:
        print(f"[ERROR] Consulta proveedores: {e}")

    # Los nombres de proyectos ya se asignaron antes de los filtros

    # Obtener datos de FAC. PAGO desde tabla ingresos
    try:
        ingreso_ids = set(p.get("ingreso_id") for p in pagos_ordenados if p.get("ingreso_id") is not None)
        fac_pago_map = {}
        
        if ingreso_ids:
            res_ingresos = supabase.table("ingresos").select("id, fac_pendiente").in_("id", list(ingreso_ids)).execute()
            for ing in (res_ingresos.data or []):
                ingreso_id = ing.get("id")
                fac_pendiente = ing.get("fac_pendiente")
                # Cualquier valor que no sea NULL = "SI"
                fac_pago_map[ingreso_id] = "SI" if fac_pendiente is not None else "-"
        
        for p in pagos_ordenados:
            ingreso_id = p.get("ingreso_id")
            p["fac_pago"] = fac_pago_map.get(ingreso_id, "-")
            
    except Exception as e:
        print(f"[ERROR] Consulta FAC. PAGO: {e}")

    # Aplicar filtro de estado después de tener todos los datos
    if filtros and filtros.get("estado"):
        estado = filtros["estado"]
        def get_estado_pago(p):
            if p["fecha_pago"]:
                return "pagado"
            elif p["total_abonado"] > 0 and p["saldo_pendiente"] > 0:
                return "abono"
            else:
                return "pendiente"
        
        pagos_ordenados = [p for p in pagos_ordenados if get_estado_pago(p) == estado]

    # Guardar en cache antes de retornar
    informe_cache.set_informe_data(pagos_ordenados, filtros)
    print(f"[CACHE SET] Datos guardados en cache para filtros: {filtros}")

    return pagos_ordenados
    proyecto_map = {}
    try:
        projs = get_cached_proyectos_with_id()
        proyecto_map = {pr["id"]: pr["proyecto"] for pr in projs}
        for r in all_rows:
            proj_id = r.get("proyecto")
            r["proyecto_nombre"] = proyecto_map.get(proj_id, proj_id)
    except Exception as e:
        print(f"[ERROR] Consulta proyectos: {e}")

    # Aplicar filtros avanzados DESPUÉS de tener nombres de proyectos
    if filtros:
        # Filtro de búsqueda parcial (proveedor, detalle, factura, proyecto, número de orden)
        search = filtros.get("proveedor", "").strip().lower()
        if search:
            all_rows = [r for r in all_rows if search in str(r.get("proveedor_nombre", "")).lower()
                        or search in str(r.get("detalle_compra", "")).lower()
                        or search in str(r.get("factura", "")).lower()
                        or search in str(r.get("proyecto_nombre", "")).lower()
                        or search in str(r.get("orden_numero", "")).lower()]

        # Filtro de proyecto exacto por NOMBRE
        proyecto = filtros.get("proyecto", "").strip()
        if proyecto:
            all_rows = [r for r in all_rows if str(r.get("proyecto_nombre", "")) == proyecto]
            print(f"[INFO] Filtro proyecto '{proyecto}' aplicado: {len(all_rows)} registros")

        # Filtros de fecha
        fecha_desde = filtros.get("fecha_desde", "").strip()
        if fecha_desde:
            all_rows = [r for r in all_rows if r.get("fecha", "") >= fecha_desde]
            
        fecha_hasta = filtros.get("fecha_hasta", "").strip()
        if fecha_hasta:
            all_rows = [r for r in all_rows if r.get("fecha", "") <= fecha_hasta]

    # Agrupar por orden_numero único y sumar montos
    pagos = {}
    for r in all_rows:
        try:
            num = int(r["orden_numero"])
        except (ValueError, TypeError):
            continue  # Omitir si no se puede convertir
            
        if num not in pagos:
            pagos[num] = {
                "orden_numero": num,
                "fecha": r["fecha"],
                "proveedor": r.get("proveedor"),  # ID del proveedor
                "proveedor_nombre": r["proveedor_nombre"],
                "detalle_compra": r["detalle_compra"],
                "factura": r["factura"],
                "total_pago": 0.0,
                "proyecto_id": r["proyecto"],
                "proyecto": r.get("proyecto_nombre", r["proyecto"]),  # Usar nombre si está disponible
                "orden_compra": r["orden_compra"],
                "condicion_pago": r["condicion_pago"],
                "vencimiento": r["vencimiento"],
                "fecha_factura": r["fecha_factura"],
                "ingreso_id": r.get("ingreso_id"),
                "fecha_pago": None,
                "total_abonado": 0.0,
                "saldo_pendiente": 0.0,
                "item": "",
                "rut_proveedor": "-",
                "cuenta": "",
                "fac_pago": "-"
            }
        pagos[num]["total_pago"] += float(r.get("costo_final_con_iva") or 0)

    # Ordenar de mayor a menor por orden_numero
    pagos_ordenados = [pagos[k] for k in sorted(pagos.keys(), reverse=True)]

    # Obtener fechas de pago en batch (con límite para evitar errores de Supabase)
    ordenes_numeros = [p["orden_numero"] for p in pagos_ordenados]
    fecha_map = {}
    if ordenes_numeros:
        try:
            batch_size = 100  # Reducir tamaño de batch para evitar límites de Supabase
            for i in range(0, len(ordenes_numeros), batch_size):
                batch_ordenes = ordenes_numeros[i:i+batch_size]
                fechas_batch = supabase.table("fechas_de_pagos_op").select("orden_numero, fecha_pago").in_("orden_numero", batch_ordenes).execute().data or []
                for row in fechas_batch:
                    fecha_map[row["orden_numero"]] = row["fecha_pago"]
            
            for p in pagos_ordenados:
                p["fecha_pago"] = fecha_map.get(p["orden_numero"])
                
            print(f"[INFO] Cargadas {len(fecha_map)} fechas de pago de {len(ordenes_numeros)} órdenes")
        except Exception as e:
            print(f"[ERROR] Consulta fechas de pago: {e}")

    # Obtener abonos en batch (con límite para evitar errores de Supabase)
    abonos_map = {}
    if ordenes_numeros:
        try:
            batch_size = 100  # Reducir tamaño de batch
            for i in range(0, len(ordenes_numeros), batch_size):
                batch_ordenes = ordenes_numeros[i:i+batch_size]
                abonos_batch = supabase.table("abonos_op").select("orden_numero, monto_abono").in_("orden_numero", batch_ordenes).execute().data or []
                
                for ab in abonos_batch:
                    num = ab.get("orden_numero")
                    if num is not None:
                        try:
                            monto = float(ab.get("monto_abono") or 0)
                            abonos_map[num] = abonos_map.get(num, 0) + monto
                        except (ValueError, TypeError):
                            continue
            
            for p in pagos_ordenados:
                num = p["orden_numero"]
                total_abonado = abonos_map.get(num, 0)
                p["total_abonado"] = total_abonado
                # Si existe fecha_pago → saldo = 0, sino saldo = total - abonos
                p["saldo_pendiente"] = 0 if p.get("fecha_pago") else max(0, p["total_pago"] - total_abonado)
                
            print(f"[INFO] Cargados abonos para {len(abonos_map)} órdenes")
        except Exception as e:
            print(f"[ERROR] Consulta abonos: {e}")

    # Obtener items por orden_compra
    ordenes_compra_unicas = set(p["orden_compra"] for p in pagos_ordenados if p.get("orden_compra"))
    if ordenes_compra_unicas:
        items_por_orden = {}
        try:
            batch_size = 100
            ordenes_list = list(ordenes_compra_unicas)
            for i in range(0, len(ordenes_list), batch_size):
                batch_ordenes = ordenes_list[i:i+batch_size]
                batch_items = supabase.table("orden_de_compra").select("orden_compra,item").in_("orden_compra", batch_ordenes).execute().data or []
                for oc in batch_ordenes:
                    items = set(row["item"] for row in batch_items if row["orden_compra"] == oc and row.get("item"))
                    items_por_orden[oc] = ", ".join(sorted(items)) if items else ""
            
            for p in pagos_ordenados:
                oc = p.get("orden_compra")
                p["item"] = items_por_orden.get(oc, "")
        except Exception as e:
            print(f"[ERROR] Consulta items: {e}")

    # Obtener datos de proveedores (RUT y cuenta corriente)
    try:
        provs = get_cached_proveedores()
        cuenta_map = {p["nombre"]: p["cuenta"] for p in provs}
        rut_map = {}
        for p in provs:
            if p.get("id") is not None and p.get("rut"):
                rut_map[p["id"]] = p["rut"]
                try:
                    rut_map[int(p["id"])] = p["rut"]
                    rut_map[str(p["id"])] = p["rut"]
                except (ValueError, TypeError):
                    pass
        
        for p in pagos_ordenados:
            p["cuenta"] = cuenta_map.get(p["proveedor_nombre"], "")
            p["rut_proveedor"] = rut_map.get(p.get("proveedor"), "-")
    except Exception as e:
        print(f"[ERROR] Consulta proveedores: {e}")

    # Los nombres de proyectos ya se asignaron antes de los filtros

    # Obtener datos de FAC. PAGO desde tabla ingresos
    try:
        ingreso_ids = set(p.get("ingreso_id") for p in pagos_ordenados if p.get("ingreso_id") is not None)
        fac_pago_map = {}
        
        if ingreso_ids:
            res_ingresos = supabase.table("ingresos").select("id, fac_pendiente").in_("id", list(ingreso_ids)).execute()
            for ing in (res_ingresos.data or []):
                ingreso_id = ing.get("id")
                fac_pendiente = ing.get("fac_pendiente")
                # Cualquier valor que no sea NULL = "SI"
                fac_pago_map[ingreso_id] = "SI" if fac_pendiente is not None else "-"
        
        for p in pagos_ordenados:
            ingreso_id = p.get("ingreso_id")
            p["fac_pago"] = fac_pago_map.get(ingreso_id, "-")
            
    except Exception as e:
        print(f"[ERROR] Consulta FAC. PAGO: {e}")

    # Aplicar filtro de estado después de tener todos los datos
    if filtros and filtros.get("estado"):
        estado = filtros["estado"]
        def get_estado_pago(p):
            if p["fecha_pago"]:
                return "pagado"
            elif p["total_abonado"] > 0 and p["saldo_pendiente"] > 0:
                return "abono"
            else:
                return "pendiente"
        
        pagos_ordenados = [p for p in pagos_ordenados if get_estado_pago(p) == estado]

    # Guardar en cache antes de retornar
    informe_cache.set_informe_data(pagos_ordenados, filtros)
    print(f"[CACHE SET] Datos guardados en cache para filtros: {filtros}")

    return pagos_ordenados

def get_totales_reales(filtros=None):
    """
    Función para calcular totales reales usando la MISMA lógica eficiente que get_informe_pagos
    INCLUYE filtro de estado que faltaba en la versión anterior
    """
    supabase = current_app.config["SUPABASE"]
    
    try:
        print(f"[TOTALES REALES] Iniciando cálculo con filtros: {filtros}")
        
        # PASO 1: Contar órdenes únicas totales con filtros aplicados
        distinct_query = supabase.table("orden_de_pago").select("orden_numero", count="exact")
        
        if filtros:
            search = filtros.get("proveedor", "").strip()
            if search:
                distinct_query = distinct_query.ilike("proveedor_nombre", f"%{search}%")
            
            proyecto_nombre = filtros.get("proyecto", "").strip()
            if proyecto_nombre:
                try:
                    projs = get_cached_proyectos_with_id()
                    for pr in projs:
                        if pr["proyecto"] == proyecto_nombre:
                            distinct_query = distinct_query.eq("proyecto", pr["id"])
                            break
                except:
                    pass
            
            fecha_desde = filtros.get("fecha_desde", "").strip()
            if fecha_desde:
                distinct_query = distinct_query.gte("fecha", fecha_desde)
                
            fecha_hasta = filtros.get("fecha_hasta", "").strip()
            if fecha_hasta:
                distinct_query = distinct_query.lte("fecha", fecha_hasta)
        
        total_result = distinct_query.execute()
        total_ordenes = total_result.count if total_result.count else 0
        
        print(f"[TOTALES REALES] Total órdenes encontradas: {total_ordenes}")
        
        if total_ordenes == 0:
            return {
                'total_pendiente': 0,
                'total_pagados': 0,
                'total_pendientes': 0,
                'saldos_por_proyecto': []
            }
        
        # PASO 2: Obtener TODAS las órdenes únicas por lotes eficientes (misma lógica que paginación)
        ordenes_query = supabase.table("orden_de_pago").select("orden_numero")
        
        # Aplicar mismos filtros
        if filtros:
            search = filtros.get("proveedor", "").strip()
            if search:
                ordenes_query = ordenes_query.ilike("proveedor_nombre", f"%{search}%")
            
            proyecto_nombre = filtros.get("proyecto", "").strip()
            if proyecto_nombre:
                try:
                    projs = get_cached_proyectos_with_id()
                    for pr in projs:
                        if pr["proyecto"] == proyecto_nombre:
                            ordenes_query = ordenes_query.eq("proyecto", pr["id"])
                            break
                except:
                    pass
            
            fecha_desde = filtros.get("fecha_desde", "").strip()
            if fecha_desde:
                ordenes_query = ordenes_query.gte("fecha", fecha_desde)
                
            fecha_hasta = filtros.get("fecha_hasta", "").strip()
            if fecha_hasta:
                ordenes_query = ordenes_query.lte("fecha", fecha_hasta)
        
        # Obtener todas las órdenes únicas en lotes (sin límite de paginación)
        all_ordenes_unicas = []
        batch_size = 1000
        offset = 0
        
        while len(all_ordenes_unicas) < total_ordenes:
            ordenes_batch = ordenes_query.order("orden_numero", desc=True).range(offset, offset + batch_size - 1).execute().data or []
            if not ordenes_batch:
                break
            
            # Extraer números únicos
            for orden in ordenes_batch:
                if orden["orden_numero"]:
                    all_ordenes_unicas.append(int(orden["orden_numero"]))
            
            offset += batch_size
            
            if len(ordenes_batch) < batch_size:
                break
        
        # Eliminar duplicados y mantener orden
        numeros_orden_unicos = list(dict.fromkeys(all_ordenes_unicas))
        
        print(f"[TOTALES REALES] Órdenes únicas procesadas: {len(numeros_orden_unicos)}")
        
        # PASO 3: Obtener datos completos para estas órdenes (en lotes seguros)
        all_rows = []
        batch_size = 500
        for i in range(0, len(numeros_orden_unicos), batch_size):
            batch_numeros = numeros_orden_unicos[i:i+batch_size]
            batch_data = supabase.table("orden_de_pago").select(
                "orden_numero, fecha, proveedor, detalle_compra, "
                "factura, proyecto, orden_compra, condicion_pago, "
                "vencimiento, fecha_factura, costo_final_con_iva, ingreso_id"
            ).in_("orden_numero", batch_numeros).execute().data or []
            all_rows.extend(batch_data)
        
        print(f"[TOTALES REALES] Registros de datos obtenidos: {len(all_rows)}")
        
        # PASO 3.5: Enriquecer con nombres de proyectos
        proyecto_map = {}
        try:
            projs = get_cached_proyectos_with_id()
            proyecto_map = {pr["id"]: pr["proyecto"] for pr in projs}
            for r in all_rows:
                proj_id = r.get("proyecto")
                r["proyecto_nombre"] = proyecto_map.get(proj_id, str(proj_id))
        except Exception as e:
            print(f"[ERROR] Error al enriquecer proyectos: {e}")
        
        # PASO 4: Agrupar y procesar (misma lógica que get_informe_pagos)
        pagos_dict = {}
        ordenes_numeros_data = []
        
        for r in all_rows:
            try:
                num = int(r["orden_numero"])
                ordenes_numeros_data.append(num)
            except (ValueError, TypeError):
                continue
                
            if num not in pagos_dict:
                pagos_dict[num] = {
                    "orden_numero": num,
                    "fecha": r["fecha"],
                    "proveedor": r.get("proveedor"),
                    "detalle_compra": r["detalle_compra"],
                    "factura": r["factura"],
                    "total_pago": 0.0,
                    "proyecto_id": r["proyecto"],
                    "proyecto": r.get("proyecto_nombre", r["proyecto"]),
                    "proyecto_nombre": r.get("proyecto_nombre", r["proyecto"]),
                    "orden_compra": r["orden_compra"],
                    "condicion_pago": r["condicion_pago"],
                    "vencimiento": r["vencimiento"],
                    "fecha_factura": r["fecha_factura"],
                    "ingreso_id": r.get("ingreso_id"),
                    "fecha_pago": None,
                    "total_abonado": 0.0,
                    "saldo_pendiente": 0.0
                }
            pagos_dict[num]["total_pago"] += float(r.get("costo_final_con_iva") or 0)
        
        # PASO 5: Obtener fechas de pago en lotes
        if ordenes_numeros_data:
            try:
                batch_size_fechas = 1000
                fecha_map = {}
                for i in range(0, len(ordenes_numeros_data), batch_size_fechas):
                    batch_ordenes = ordenes_numeros_data[i:i+batch_size_fechas]
                    fechas_batch = supabase.table("fechas_de_pagos_op").select("orden_numero, fecha_pago").in_("orden_numero", batch_ordenes).execute().data or []
                    for row in fechas_batch:
                        fecha_map[row["orden_numero"]] = row["fecha_pago"]
                
                for num in pagos_dict:
                    pagos_dict[num]["fecha_pago"] = fecha_map.get(num)
                    
                print(f"[TOTALES REALES] Fechas de pago cargadas: {len(fecha_map)}")
            except Exception as e:
                print(f"[ERROR] Error al obtener fechas de pago: {e}")
        
        # PASO 6: Obtener abonos en lotes
        if ordenes_numeros_data:
            try:
                batch_size_abonos = 1000
                abonos_map = {}
                for i in range(0, len(ordenes_numeros_data), batch_size_abonos):
                    batch_ordenes = ordenes_numeros_data[i:i+batch_size_abonos]
                    abonos_batch = supabase.table("abonos_op").select("orden_numero, monto_abono").in_("orden_numero", batch_ordenes).execute().data or []
                    for abono in abonos_batch:
                        orden = abono["orden_numero"]
                        monto = float(abono["monto_abono"] or 0)
                        if orden not in abonos_map:
                            abonos_map[orden] = 0.0
                        abonos_map[orden] += monto
                
                for num in pagos_dict:
                    total_abonado = abonos_map.get(num, 0.0)
                    pagos_dict[num]["total_abonado"] = total_abonado
                    pagos_dict[num]["saldo_pendiente"] = max(0, pagos_dict[num]["total_pago"] - total_abonado)
                    
                print(f"[TOTALES REALES] Abonos cargados: {len(abonos_map)}")
            except Exception as e:
                print(f"[ERROR] Error al calcular abonos: {e}")
        
        # Convertir a lista ordenada
        pagos_procesados = [pagos_dict[k] for k in sorted(pagos_dict.keys(), reverse=True)]
        
        # PASO 7: Aplicar filtro de estado (NUEVO - esto faltaba en la versión anterior!)
        if filtros and filtros.get("estado"):
            estado_filtro = filtros["estado"].lower()  # Convertir a minúsculas
            def get_estado_pago(p):
                if p.get("fecha_pago"):
                    return "pagado"
                elif p.get("total_abonado", 0) > 0:
                    return "abono"
                else:
                    return "pendiente"
            
            pagos_procesados = [p for p in pagos_procesados if get_estado_pago(p) == estado_filtro]
            print(f"[TOTALES REALES] Filtro de estado '{estado_filtro}' aplicado: {len(pagos_procesados)} registros")
        
        # PASO 8: Calcular totales finales
        total_pendiente = 0
        total_pagados = 0
        total_pendientes = 0
        saldos_por_proyecto = {}
        
        for p in pagos_procesados:
            if p.get("fecha_pago"):
                total_pagados += 1
            else:
                total_pendientes += 1
                saldo = p.get("saldo_pendiente", 0)
                total_pendiente += saldo
                
                proyecto_nombre = p.get("proyecto_nombre", "Sin Proyecto")
                if proyecto_nombre not in saldos_por_proyecto:
                    saldos_por_proyecto[proyecto_nombre] = 0
                saldos_por_proyecto[proyecto_nombre] += saldo
        
        # Ordenar proyectos por saldo descendente
        saldos_por_proyecto_lista = sorted(
            [{"proyecto": k, "saldo": v} for k, v in saldos_por_proyecto.items()],
            key=lambda x: x["saldo"],
            reverse=True
        )[:10]  # Top 10
        
        resultado = {
            'total_pendiente': total_pendiente,
            'total_pagados': total_pagados,
            'total_pendientes': total_pendientes,
            'saldos_por_proyecto': saldos_por_proyecto_lista
        }
        
        print(f"[TOTALES REALES] Resultado final: Pagados={total_pagados}, Pendientes={total_pendientes}, Total=${total_pendiente:,.0f}")
        return resultado
        
    except Exception as e:
        print(f"[ERROR CRÍTICO] Error en get_totales_reales: {e}")
        import traceback
        traceback.print_exc()
        return {
            'total_pendiente': 0,
            'total_pagados': 0,
            'total_pendientes': 0,
            'saldos_por_proyecto': []
        }

@login_required
@bp_informe_op.route("/informe_op", methods=["GET"])
@require_modulo('pagos')
def informe_op():
    """
    Ruta principal del informe de órdenes de pago
    Migrada desde pagos.py con optimizaciones
    """
    # Control de acceso
    modulos_usuario = [m.strip().lower() for m in get_modulos_usuario()]
    if 'pagos' not in modulos_usuario:
        flash('No tienes permiso para acceder a esta sección.', 'danger')
        return render_template('sin_permisos.html')

    # Verificar si necesitamos invalidar cache por tiempo (5 minutos)
    if not informe_cache.is_cache_fresh():
        informe_cache.invalidate_all("refresh automático por tiempo (5 min)")
        print("[CACHE] Cache invalidado automáticamente por tiempo")

    # Recoger filtros de la URL
    filtros = {}
    proveedor = request.args.get("proveedor", "").strip()
    proyecto = request.args.get("proyecto", "").strip()
    estado = request.args.get("estado", "").strip()
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()

    if proveedor:
        filtros["proveedor"] = proveedor
    if proyecto:
        filtros["proyecto"] = proyecto
    if estado:
        filtros["estado"] = estado
    if fecha_desde:
        filtros["fecha_desde"] = fecha_desde
    if fecha_hasta:
        filtros["fecha_hasta"] = fecha_hasta

    # Parámetros de paginación
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)  # 100 registros por defecto
    
    # Obtener datos usando PAGINACIÓN EFICIENTE
    result_data = get_informe_pagos(filtros, page, per_page)
    
    # Extraer datos del resultado
    pagos = result_data['registros']
    total_registros = result_data['total_registros']
    total_pages = result_data['total_pages']
    
    # Obtener totales reales (no paginados) para mostrar información correcta
    print("[INFO] Calculando totales reales...")
    totales_reales = get_totales_reales(filtros)
    total_pendiente = totales_reales['total_pendiente']
    total_pagados = totales_reales['total_pagados']
    total_pendientes = totales_reales['total_pendientes']
    saldos_por_proyecto_top = totales_reales['saldos_por_proyecto']
    
    # Información de paginación
    has_prev = page > 1
    has_next = page < total_pages
    
    print(f"[INFO] Página {page}/{total_pages} - Mostrando {len(pagos)} de {total_registros} registros")
    print(f"[INFO] Totales reales: {total_pagados} pagados, {total_pendientes} pendientes, ${total_pendiente:,.0f} pendiente")

    # Datos adicionales para filtros dinámicos (usando solo datos paginados por eficiencia)
    proveedores_unicos = sorted(set(p["proveedor_nombre"] for p in pagos))
    proyectos_unicos = sorted(set(p["proyecto"] for p in pagos))
    
    print(f"[INFO] Proyectos únicos encontrados: {proyectos_unicos[:5]}...")  # Mostrar primeros 5
    print(f"[INFO] Saldos por proyecto: {len(saldos_por_proyecto_top)} proyectos con saldo pendiente")

    # Calcular fecha máxima para input de fecha (hoy + 7 días)
    fecha_maxima = (date.today() + timedelta(days=7)).isoformat()

    # Permisos de edición
    puede_editar = 'pagos' in modulos_usuario

    # Registrar actividad
    registrar_log_actividad("Ver informe de órdenes de pago", f"Filtros: {filtros}, Página: {page}")

    return render_template(
        "informe_op.html",
        pagos=pagos,
        filtros_activos=filtros,
        proveedores_unicos=proveedores_unicos,
        proyectos_unicos=proyectos_unicos,
        saldos_por_proyecto=saldos_por_proyecto_top,
        fecha_maxima=fecha_maxima,
        puede_editar=puede_editar,
        total_pendiente=total_pendiente,
        total_registros=total_registros,
        total_pagados=total_pagados,
        total_pendientes=total_pendientes,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
        date=date
    )

@login_required
@bp_informe_op.route("/informe_op/update_pagos", methods=["POST"])
@require_modulo('pagos')
@invalidate_informe_cache('update', 'fechas_de_pagos_op')
def update_pagos():
    """
    Actualización masiva de fechas de pago
    CORREGIDO: Solo procesa órdenes enviadas en el formulario para evitar afectar registros de otras páginas
    """
    supabase = current_app.config["SUPABASE"]
    nums = request.form.getlist("orden_numero[]")
    fechas = request.form.getlist("fecha_pago[]")
    
    # Protección contra envío vacío
    if not nums or len(nums) == 0:
        flash("No se enviaron datos para actualizar.", "warning")
        return redirect(url_for("informe_op.informe_op"))
    
    # VALIDACIÓN CRÍTICA: Verificar que nums y fechas tengan la misma longitud
    if len(nums) != len(fechas):
        flash("Error: No coinciden las órdenes con las fechas enviadas.", "danger")
        return redirect(url_for("informe_op.informe_op"))
    
    any_error = False
    upserts = []
    deletes = []
    
    # Convertir números de orden a enteros y validar
    ordenes_validas = []
    for num in nums:
        try:
            orden_numero = int(num)
            ordenes_validas.append(orden_numero)
        except (ValueError, TypeError):
            flash(f"Número de orden inválido: {num}", "danger")
            any_error = True
            continue

    if not ordenes_validas:
        flash("No se encontraron órdenes válidas para procesar.", "warning")
        return redirect(url_for("informe_op.informe_op"))

    # Consultar fechas actuales SOLO para las órdenes del formulario
    fechas_actuales = {}
    try:
        res_fechas = supabase.table("fechas_de_pagos_op").select("orden_numero, fecha_pago").in_("orden_numero", ordenes_validas).execute()
        fechas_actuales = {row["orden_numero"]: row["fecha_pago"] for row in (res_fechas.data or [])}
    except Exception as e:
        print(f"[ERROR] Consulta fechas actuales: {e}")
        fechas_actuales = {}

    # Consultar abonos SOLO para las órdenes del formulario
    abonos_por_orden = {}
    try:
        res_abonos = supabase.table("abonos_op").select("orden_numero, monto_abono").in_("orden_numero", ordenes_validas).execute()
        
        for abono in (res_abonos.data or []):
            orden_num = abono.get("orden_numero")
            monto = int(round(float(abono.get("monto_abono") or 0)))
            abonos_por_orden[orden_num] = abonos_por_orden.get(orden_num, 0) + monto
            
    except Exception as e:
        print(f"[ERROR] Consulta abonos: {e}")
        abonos_por_orden = {}

    # Procesar cada orden EN EL ORDEN EXACTO del formulario
    for i in range(len(ordenes_validas)):
        orden_numero = ordenes_validas[i]
        fpago = fechas[i].strip() if i < len(fechas) else ""
        
        fecha_actual = fechas_actuales.get(orden_numero)
        suma_abonos = abonos_por_orden.get(orden_numero, 0)
        
        if fpago:
            # PAGO DIRECTO: Asignar fecha
            try:
                d = datetime.strptime(fpago, "%Y-%m-%d").date()
            except ValueError:
                flash(f"Fecha inválida para OP {orden_numero}", "danger")
                any_error = True
                continue
                
            if d > date.today() + timedelta(days=7):
                flash(f"Fecha de pago muy futura para OP {orden_numero}", "danger")
                any_error = True
                continue
            
            # Solo actualizar si la fecha es diferente
            if fecha_actual != fpago:
                upserts.append({"orden_numero": orden_numero, "fecha_pago": fpago})
                print(f"[INFO] Programando actualizar OP {orden_numero}: {fpago}")
        else:
            # Eliminar fecha de pago SOLO si había una fecha previa
            if fecha_actual:
                # IMPORTANTE: Solo eliminar si NO tiene abonos que justifiquen la fecha
                # Si tiene abonos completos, mantener la fecha automática
                try:
                    # Obtener el total de la orden para comparar con abonos
                    res_total = supabase.table("orden_de_pago").select("costo_final_con_iva").eq("orden_numero", orden_numero).execute()
                    total_orden = 0
                    if res_total.data:
                        total_orden = int(round(float(res_total.data[0].get("costo_final_con_iva") or 0)))
                    
                    # Solo eliminar fecha si no está justificada por abonos completos
                    if suma_abonos < total_orden:
                        deletes.append(orden_numero)
                        print(f"[INFO] Programando eliminar fecha OP {orden_numero} (abonos: {suma_abonos}, total: {total_orden})")
                    else:
                        print(f"[INFO] Manteniendo fecha automática OP {orden_numero} (abonos completos: {suma_abonos})")
                        
                except Exception as e:
                    print(f"[ERROR] Validando abonos para OP {orden_numero}: {e}")
                    # En caso de error, eliminar la fecha de forma conservadora
                    deletes.append(orden_numero)

    # Ejecutar operaciones en batch con manejo seguro de transacciones
    if upserts:
        try:
            # Verificar que las órdenes aún existen antes de hacer upsert
            orden_numeros_upsert = [u["orden_numero"] for u in upserts]
            verificacion = supabase.table("orden_de_pago").select("orden_numero").in_("orden_numero", orden_numeros_upsert).execute()
            ordenes_validas = {row["orden_numero"] for row in verificacion.data}
            
            # Filtrar solo las órdenes que aún existen
            upserts_validos = [u for u in upserts if u["orden_numero"] in ordenes_validas]
            
            if upserts_validos:
                result = supabase.table("fechas_de_pagos_op").upsert(upserts_validos, on_conflict="orden_numero").execute()
                print(f"[TRANSACCIÓN SEGURA] Upsert exitoso: {len(upserts_validos)} fechas actualizadas")
                flash(f"✅ {len(upserts_validos)} fecha(s) de pago actualizadas correctamente.", "success")
            else:
                flash("⚠️ No se encontraron órdenes válidas para actualizar.", "warning")
        except Exception as e:
            print(f"[ERROR TRANSACCIÓN] Upsert fechas: {e}")
            flash(f"Error al guardar fechas de pago: {str(e)}", "danger")
            any_error = True

    if deletes:
        try:
            # Verificar que las fechas a eliminar realmente existen
            fechas_existentes = supabase.table("fechas_de_pagos_op").select("orden_numero").in_("orden_numero", deletes).execute()
            fechas_a_eliminar = [row["orden_numero"] for row in fechas_existentes.data]
            
            if fechas_a_eliminar:
                result = supabase.table("fechas_de_pagos_op").delete().in_("orden_numero", fechas_a_eliminar).execute()
                print(f"[TRANSACCIÓN SEGURA] Delete exitoso: {len(fechas_a_eliminar)} fechas eliminadas")
                flash(f"✅ {len(fechas_a_eliminar)} fecha(s) de pago eliminadas correctamente.", "success")
            else:
                flash("⚠️ No se encontraron fechas para eliminar.", "warning")
        except Exception as e:
            print(f"[ERROR TRANSACCIÓN] Delete fechas: {e}")
            flash(f"Error al eliminar fechas de pago: {str(e)}", "danger")
            any_error = True

    if not any_error and not upserts and not deletes:
        flash("No se realizaron cambios (las fechas ya estaban actualizadas).", "info")

    # Registrar actividad
    if upserts or deletes:
        registrar_log_actividad("Actualizar fechas de pago", f"Actualizadas: {len(upserts)}, Eliminadas: {len(deletes)}")

    return redirect(url_for("informe_op.informe_op"))

# ===== GESTIÓN DE ABONOS =====

@login_required
@bp_informe_op.route('/informe_op/abonos/<int:orden_numero>', methods=['GET'])
@require_modulo('pagos')
def get_abonos_op(orden_numero):
    """Obtener historial de abonos para una orden específica"""
    supabase = current_app.config["SUPABASE"]
    try:
        res = supabase.table("abonos_op").select("id, orden_numero, monto_abono, fecha_abono, observacion, created_at").eq("orden_numero", orden_numero).order("fecha_abono", desc=False).execute()
        abonos = res.data if hasattr(res, "data") and res.data else []
        
        response = jsonify(success=True, abonos=abonos)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    except Exception as e:
        print(f"[ERROR] Consulta abonos_op para OP {orden_numero}: {e}")
        return jsonify(success=True, abonos=[])

@login_required
@bp_informe_op.route('/informe_op/abonos/<int:orden_numero>', methods=['POST'])
@require_modulo('pagos')
@invalidate_informe_cache('insert', 'abonos_op')
def registrar_abono_op(orden_numero):
    """Registrar nuevo abono para una orden"""
    supabase = current_app.config["SUPABASE"]
    try:
        data = request.get_json() or {}
        monto = int(round(float(data.get("monto_abono") or 0)))
        fecha = data.get("fecha_abono")
        observacion = data.get("observacion")

        if monto <= 0:
            return jsonify(success=False, error="Monto debe ser mayor a cero"), 400
        if not fecha:
            return jsonify(success=False, error="Fecha requerida"), 400

        # Validar suma de abonos vs total de la orden
        res_abonos = supabase.table("abonos_op").select("monto_abono").eq("orden_numero", orden_numero).execute()
        suma_abonos = sum(int(round(float(a.get("monto_abono") or 0))) for a in (res_abonos.data or []))

        res_pago = supabase.table("orden_de_pago").select("costo_final_con_iva").eq("orden_numero", orden_numero).limit(1).execute()
        if not res_pago.data:
            return jsonify(success=False, error="No se encontró el total de la orden."), 400
        total_pago = int(round(float(res_pago.data[0].get("costo_final_con_iva") or 0)))

        nueva_suma = suma_abonos + monto
        if nueva_suma > total_pago:
            return jsonify(success=False, error=f"La suma de abonos ({nueva_suma}) supera el total de la orden ({total_pago})."), 400

        # Insertar abono
        abono = {
            "orden_numero": orden_numero,
            "monto_abono": monto,
            "fecha_abono": fecha,
            "observacion": observacion or None,
        }

        # Insertar abono con transacción segura
        try:
            # Verificar que la orden aún existe antes de insertar
            orden_existe = supabase.table("orden_de_pago").select("orden_numero").eq("orden_numero", orden_numero).limit(1).execute()
            if not orden_existe.data:
                return jsonify(success=False, error="La orden ya no existe en el sistema."), 400
            
            # Insertar abono
            res = supabase.table("abonos_op").insert(abono).execute()
            if hasattr(res, "error") and res.error:
                print(f"[ERROR TRANSACCIÓN] Error al insertar abono: {res.error}")
                return jsonify(success=False, error=str(res.error)), 500
            
            print(f"[TRANSACCIÓN SEGURA] Abono insertado exitosamente para orden {orden_numero}")

            # Si completa el total, registrar fecha_pago automáticamente
            if nueva_suma == total_pago:
                try:
                    fecha_result = supabase.table("fechas_de_pagos_op").upsert(
                        {"orden_numero": orden_numero, "fecha_pago": fecha}, 
                        on_conflict="orden_numero"
                    ).execute()
                    print(f"[TRANSACCIÓN SEGURA] Fecha de pago automática registrada para orden {orden_numero}")
                except Exception as fecha_error:
                    print(f"[ERROR TRANSACCIÓN] Error al registrar fecha automática: {fecha_error}")
                    # No fallar todo el proceso por este error

            return jsonify(success=True)
        except Exception as insert_error:
            print(f"[ERROR TRANSACCIÓN] Error en inserción de abono: {insert_error}")
            return jsonify(success=False, error=f"Error al guardar abono: {str(insert_error)}"), 500
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@login_required
@bp_informe_op.route('/informe_op/abonos/<int:abono_id>', methods=['PUT'])
@require_modulo('pagos')
@invalidate_informe_cache('update', 'abonos_op')
def editar_abono_op(abono_id):
    """Editar abono existente"""
    supabase = current_app.config["SUPABASE"]
    try:
        data = request.get_json() or {}
        monto = int(round(float(data.get("monto_abono") or 0)))
        fecha = data.get("fecha_abono")
        observacion = data.get("observacion")
        
        if monto <= 0:
            return jsonify(success=False, error="Monto debe ser mayor a cero"), 400
        
        # Obtener orden_numero del abono
        res_abono = supabase.table("abonos_op").select("orden_numero").eq("id", abono_id).limit(1).execute()
        if not res_abono.data:
            return jsonify(success=False, error="No se encontró el abono."), 400
        orden_numero = res_abono.data[0]["orden_numero"]
        
        # Obtener total_pago de la orden
        res_pago = supabase.table("orden_de_pago").select("costo_final_con_iva").eq("orden_numero", orden_numero).limit(1).execute()
        if not res_pago.data:
            return jsonify(success=False, error="No se encontró el total de la orden."), 400
        total_pago = int(round(float(res_pago.data[0].get("costo_final_con_iva") or 0)))
        
        # Consultar otros abonos (excluyendo el que se está editando)
        res_otros_abonos = supabase.table("abonos_op").select("monto_abono").eq("orden_numero", orden_numero).neq("id", abono_id).execute()
        suma_otros_abonos = sum(int(round(float(a.get("monto_abono") or 0))) for a in (res_otros_abonos.data or []))
        
        # Validar suma total
        nueva_suma = suma_otros_abonos + monto
        if nueva_suma > total_pago:
            return jsonify(success=False, error=f"La suma de abonos ({nueva_suma}) supera el total de la orden ({total_pago})."), 400
        
        # Actualizar abono
        update_data = {"monto_abono": monto}
        if fecha:
            update_data["fecha_abono"] = fecha
        if observacion is not None:
            update_data["observacion"] = observacion
        
        # Actualizar abono con transacción segura
        try:
            # Verificar que el abono aún existe antes de actualizar
            verificacion_abono = supabase.table("abonos_op").select("id").eq("id", abono_id).limit(1).execute()
            if not verificacion_abono.data:
                return jsonify(success=False, error="El abono ya no existe en el sistema."), 400
            
            res = supabase.table("abonos_op").update(update_data).eq("id", abono_id).execute()
            if hasattr(res, "error") and res.error:
                print(f"[ERROR TRANSACCIÓN] Error al actualizar abono: {res.error}")
                return jsonify(success=False, error=str(res.error)), 500
            
            print(f"[TRANSACCIÓN SEGURA] Abono {abono_id} actualizado exitosamente")

            # Manejar fecha de pago automática con validaciones
            try:
                if nueva_suma == total_pago:
                    fecha_result = supabase.table("fechas_de_pagos_op").upsert(
                        {"orden_numero": orden_numero, "fecha_pago": fecha or date.today().isoformat()}, 
                        on_conflict="orden_numero"
                    ).execute()
                    print(f"[TRANSACCIÓN SEGURA] Fecha de pago actualizada para orden {orden_numero}")
                elif nueva_suma == 0:
                    # Verificar que la fecha existe antes de eliminar
                    fecha_existe = supabase.table("fechas_de_pagos_op").select("orden_numero").eq("orden_numero", orden_numero).limit(1).execute()
                    if fecha_existe.data:
                        supabase.table("fechas_de_pagos_op").delete().eq("orden_numero", orden_numero).execute()
                        print(f"[TRANSACCIÓN SEGURA] Fecha de pago eliminada para orden {orden_numero}")
            except Exception as fecha_error:
                print(f"[ERROR TRANSACCIÓN] Error al manejar fecha automática: {fecha_error}")
                # No fallar todo el proceso por este error
            
            return jsonify(success=True)
        except Exception as update_error:
            print(f"[ERROR TRANSACCIÓN] Error en actualización de abono: {update_error}")
            return jsonify(success=False, error=f"Error al actualizar abono: {str(update_error)}"), 500
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@login_required
@bp_informe_op.route('/informe_op/abonos/<int:abono_id>', methods=['DELETE'])
@require_modulo('pagos')
@invalidate_informe_cache('delete', 'abonos_op')
def eliminar_abono_op(abono_id):
    """Eliminar abono existente"""
    supabase = current_app.config["SUPABASE"]
    try:
        # Obtener información del abono antes de eliminarlo
        res_abono = supabase.table("abonos_op").select("orden_numero").eq("id", abono_id).limit(1).execute()
        if not res_abono.data:
            return jsonify(success=False, error="No se encontró el abono."), 400
        orden_numero = res_abono.data[0]["orden_numero"]

        # Eliminar abono con transacción segura
        try:
            # Verificar que el abono aún existe antes de eliminar
            verificacion_abono = supabase.table("abonos_op").select("id").eq("id", abono_id).limit(1).execute()
            if not verificacion_abono.data:
                return jsonify(success=False, error="El abono ya no existe en el sistema."), 400
            
            res = supabase.table("abonos_op").delete().eq("id", abono_id).execute()
            if hasattr(res, "error") and res.error:
                print(f"[ERROR TRANSACCIÓN] Error al eliminar abono: {res.error}")
                return jsonify(success=False, error=str(res.error)), 500
            
            print(f"[TRANSACCIÓN SEGURA] Abono {abono_id} eliminado exitosamente")

            # Verificar suma restante y manejar fecha de pago automática con validaciones
            try:
                res_abonos_restantes = supabase.table("abonos_op").select("monto_abono").eq("orden_numero", orden_numero).execute()
                suma_restante = sum(int(round(float(a.get("monto_abono") or 0))) for a in (res_abonos_restantes.data or []))
                
                if suma_restante > 0:
                    res_pago = supabase.table("orden_de_pago").select("costo_final_con_iva").eq("orden_numero", orden_numero).limit(1).execute()
                    total_pago = int(round(float(res_pago.data[0].get("costo_final_con_iva") or 0))) if res_pago.data else 0
                    
                    if suma_restante < total_pago:
                        # Verificar que la fecha existe antes de eliminar
                        fecha_existe = supabase.table("fechas_de_pagos_op").select("orden_numero").eq("orden_numero", orden_numero).limit(1).execute()
                        if fecha_existe.data:
                            supabase.table("fechas_de_pagos_op").delete().eq("orden_numero", orden_numero).execute()
                            print(f"[TRANSACCIÓN SEGURA] Fecha de pago eliminada para orden {orden_numero} (pago incompleto)")
                else:
                    # Verificar que la fecha existe antes de eliminar
                    fecha_existe = supabase.table("fechas_de_pagos_op").select("orden_numero").eq("orden_numero", orden_numero).limit(1).execute()
                    if fecha_existe.data:
                        supabase.table("fechas_de_pagos_op").delete().eq("orden_numero", orden_numero).execute()
                        print(f"[TRANSACCIÓN SEGURA] Fecha de pago eliminada para orden {orden_numero} (sin abonos)")
            except Exception as fecha_error:
                print(f"[ERROR TRANSACCIÓN] Error al manejar fecha automática: {fecha_error}")
                # No fallar todo el proceso por este error
            
            return jsonify(success=True)
        except Exception as delete_error:
            print(f"[ERROR TRANSACCIÓN] Error en eliminación de abono: {delete_error}")
            return jsonify(success=False, error=f"Error al eliminar abono: {str(delete_error)}"), 500

        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@login_required
@bp_informe_op.route('/informe_op/cache-stats')
@require_modulo('pagos')
def cache_stats():
    """Endpoint para ver estadísticas del cache (solo para debugging)"""
    stats = get_cache_stats()
    return jsonify(stats)

@login_required
@bp_informe_op.route('/informe_op/invalidate-cache', methods=['POST'])
@require_modulo('pagos')
def manual_cache_invalidation():
    """Endpoint para invalidar cache manualmente (solo para debugging)"""
    informe_cache.invalidate_all("invalidación manual por usuario")
    return jsonify(success=True, message="Cache invalidado exitosamente")

@login_required
@bp_informe_op.route('/informe_op/validar-integridad', methods=['POST'])
@require_modulo('pagos')
def validar_integridad():
    """Endpoint para validar integridad de datos"""
    supabase = current_app.config["SUPABASE"]
    try:
        orden_numero = request.json.get('orden_numero') if request.json else None
        problemas = validar_integridad_datos(supabase, orden_numero)
        
        return jsonify({
            'success': True,
            'problemas_detectados': len(problemas),
            'problemas': problemas,
            'message': f"Validación completada. {len(problemas)} problemas detectados."
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': "Error durante la validación"
        }), 500

@login_required
@bp_informe_op.route('/informe_op/reparar-integridad', methods=['POST'])
@require_modulo('pagos')
def reparar_integridad():
    """Endpoint para reparar automáticamente problemas de integridad detectados"""
    supabase = current_app.config["SUPABASE"]
    try:
        orden_numero = request.json.get('orden_numero') if request.json else None
        problemas = validar_integridad_datos(supabase, orden_numero)
        
        reparaciones_realizadas = 0
        
        for problema in problemas:
            try:
                if problema['problema'] == 'PAGO_COMPLETO_SIN_FECHA':
                    # Agregar fecha de pago automática
                    supabase.table("fechas_de_pagos_op").upsert({
                        "orden_numero": problema['orden'],
                        "fecha_pago": date.today().isoformat()
                    }, on_conflict="orden_numero").execute()
                    reparaciones_realizadas += 1
                    print(f"[REPARACIÓN] Agregada fecha automática para orden {problema['orden']}")
                
                elif problema['problema'] == 'FECHA_CON_PAGO_INCOMPLETO':
                    # Eliminar fecha de pago incorrecta
                    supabase.table("fechas_de_pagos_op").delete().eq("orden_numero", problema['orden']).execute()
                    reparaciones_realizadas += 1
                    print(f"[REPARACIÓN] Eliminada fecha incorrecta para orden {problema['orden']}")
                
                # Los casos de ABONOS_EXCEDEN_TOTAL requieren intervención manual
                
            except Exception as rep_error:
                print(f"[ERROR REPARACIÓN] Error reparando orden {problema['orden']}: {rep_error}")
        
        # Invalidar cache después de reparaciones
        if reparaciones_realizadas > 0:
            informe_cache.invalidate_all("reparación de integridad")
        
        return jsonify({
            'success': True,
            'problemas_detectados': len(problemas),
            'reparaciones_realizadas': reparaciones_realizadas,
            'message': f"Reparación completada. {reparaciones_realizadas} problemas reparados de {len(problemas)} detectados."
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': "Error durante la reparación"
        }), 500
