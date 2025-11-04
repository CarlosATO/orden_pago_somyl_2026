"""
Módulo de órdenes no recepcionadas adaptado para trabajar con frontend React
CORREGIDO: Muestra OCs con al menos una línea pendiente y suma solo montos pendientes
"""

from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required
from datetime import datetime, date
from collections import Counter

bp = Blueprint("ordenes_no_recepcionadas", __name__)

# Flag usada en la BD para marcar OCs que deben excluirse del informe.
# En el sistema de producción este valor es "1" (no "SI").
ELIMINA_OC_FLAG = "1"


def safe_str(value):
    """Convierte valor a string de forma segura"""
    return str(value) if value is not None else ""


def safe_float(value):
    """Convierte valor a float de forma segura"""
    try:
        return float(value) if value else 0.0
    except (ValueError, TypeError):
        return 0.0


def normalize_art_corr(value):
    """Normaliza art_corr para comparación"""
    if value is None:
        return ""
    return str(value).strip().upper()


def get_proveedores_map(supabase):
    """Obtiene mapeo de proveedores"""
    try:
        response = supabase.table("proveedores").select("id, nombre").execute()
        return {str(p['id']): p['nombre'] for p in (response.data or [])}
    except Exception:
        return {}


def get_all_ingresos(supabase):
    """Obtiene todos los ingresos con paginación (CRÍTICO: sin esto solo trae 1000 registros)"""
    all_ingresos = []
    start = 0
    page_size = 1000
    
    try:
        while True:
            response = supabase.table("ingresos").select("orden_compra, art_corr").range(
                start, start + page_size - 1
            ).execute()
            rows = response.data or []
            
            if not rows:
                break
            
            all_ingresos.extend(rows)
            
            # Si recibimos menos registros que el tamaño de página, ya terminamos
            if len(rows) < page_size:
                break
            
            start += page_size
        
        return all_ingresos
    except Exception as e:
        current_app.logger.error(f"Error obteniendo ingresos: {e}")
        return []


def create_ingresos_set(ingresos):
    """Crea set de tuplas (oc, art_corr) para búsqueda rápida"""
    # Construimos el set usando la tupla (orden_compra, art_corr) para que
    # la comparación se haga por línea (igual que el sistema original).
    # art_corr se normaliza para evitar errores de formato/espacios.
    ingresos_set = set()
    for ing in ingresos:
        oc = safe_str(ing.get("orden_compra"))
        art = normalize_art_corr(ing.get("art_corr"))
        if oc:
            ingresos_set.add((oc, art))
    return ingresos_set


@bp.route("/lista", methods=["GET"])
@token_required
def lista_ordenes_pendientes(current_user):
    """
    Devuelve lista de órdenes de compra pendientes (no recepcionadas)
    LÓGICA CORREGIDA: Muestra OCs con AL MENOS UNA línea pendiente
    y suma SOLO el monto de las líneas pendientes
    FILTRO: Solo muestra OCs del último año (mismo comportamiento que producción)
    """
    try:
        supabase = current_app.config['SUPABASE']
        
        current_app.logger.info("Iniciando consulta de órdenes pendientes")
        
        # Calcular fecha límite (último año - 12 meses)
        from datetime import datetime, timedelta
        fecha_limite = (datetime.now() - timedelta(days=365)).date().isoformat()
        
        current_app.logger.info(f"Filtrando OCs desde: {fecha_limite}")
        
        # CRÍTICO: Obtener TODAS las líneas de OC con paginación
        oc_lines = []
        start = 0
        page_size = 1000
        
        while True:
            response = supabase.table("orden_de_compra").select(
                "orden_compra, proveedor, fecha, total, art_corr, elimina_oc"
            ).gte("fecha", fecha_limite).order("orden_compra", desc=True).range(
                start, start + page_size - 1
            ).execute()
            
            rows = response.data or []
            if not rows:
                break
            
            oc_lines.extend(rows)
            
            if len(rows) < page_size:
                break
            
            start += page_size
        
        current_app.logger.info(f"Total líneas OC obtenidas CON PAGINACIÓN (desde {fecha_limite}): {len(oc_lines)}")
        
        # Filtrar OCs que no estén marcadas como eliminadas (usar la bandera definida)
        oc_lines = [ln for ln in oc_lines if safe_str(ln.get("elimina_oc")) != ELIMINA_OC_FLAG]
        current_app.logger.info(f"Líneas después de filtrar eliminadas: {len(oc_lines)}")
        
        # Obtener mapeo de proveedores
        proveedor_map = get_proveedores_map(supabase)
        
        # Obtener todos los ingresos
        ingresos = get_all_ingresos(supabase)
        ingresos_set = create_ingresos_set(ingresos)
        current_app.logger.info(f"Total ingresos registrados: {len(ingresos)}")
        
        # Procesar OCs pendientes línea por línea (igual que sistema antiguo)
        # Una OC se muestra si tiene AL MENOS UNA línea sin ingreso
        # y se suma SOLO el monto de las líneas pendientes
        oc_pendientes = {}
        for ln in oc_lines:
            oc = safe_str(ln.get("orden_compra"))
            if not oc:
                continue
            
            proveedor_id = safe_str(ln.get("proveedor"))
            proveedor = proveedor_map.get(proveedor_id, proveedor_id)
            fecha = ln.get("fecha")
            monto_total = safe_float(ln.get("total"))
            
            art_corr = normalize_art_corr(ln.get("art_corr"))
            clave = (oc, art_corr)
            
            # Si esta línea NO está en ingresos, es pendiente
            if clave not in ingresos_set:
                if oc not in oc_pendientes:
                    oc_pendientes[oc] = {
                        "orden_compra": oc,
                        "proveedor": proveedor,
                        "proveedor_id": proveedor_id,
                        "fecha": fecha,
                        "monto_total": 0.0,
                        "estado": "Pendiente"
                    }
                # Sumar solo el monto de esta línea pendiente
                oc_pendientes[oc]["monto_total"] += monto_total
        
        # Preparar respuesta
        pendientes = list(oc_pendientes.values())
        total_oc = len(pendientes)
        total_monto = sum(p["monto_total"] for p in pendientes)
        
        current_app.logger.info(f"Total OCs pendientes: {total_oc}, Monto total: {total_monto}")
        
        return jsonify({
            "success": True,
            "data": pendientes,
            "total_oc": total_oc,
            "total_monto": total_monto
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en lista_ordenes_pendientes: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error al obtener órdenes pendientes: {str(e)}"
        }), 500


@bp.route("/detalle/<oc_numero>", methods=["GET"])
@token_required
def detalle_orden(current_user, oc_numero):
    """
    Devuelve el detalle completo de una orden de compra específica
    """
    try:
        supabase = current_app.config['SUPABASE']
        
        current_app.logger.info(f"Obteniendo detalle de OC: {oc_numero}")
        
        # Obtener todas las líneas de la OC
        response = supabase.table("orden_de_compra").select(
            "orden_compra, proveedor, fecha, codigo, descripcion, cantidad, precio_unitario, total, tipo, art_corr"
        ).eq("orden_compra", oc_numero).execute()
        
        lineas_oc = response.data or []
        
        if not lineas_oc:
            return jsonify({
                "success": False,
                "message": f"OC {oc_numero} no encontrada"
            }), 404
        
        # Obtener proveedor
        proveedor_id = safe_str(lineas_oc[0].get("proveedor"))
        proveedor_map = get_proveedores_map(supabase)
        proveedor = proveedor_map.get(proveedor_id, proveedor_id)
        
        # Formatear fecha para JSON si es necesario
        fecha_val = lineas_oc[0].get("fecha")
        if isinstance(fecha_val, (datetime, date)):
            fecha_val = fecha_val.isoformat()

        # Obtener ingresos de esta OC
        ingresos_response = supabase.table("ingresos").select("art_corr").eq("orden_compra", oc_numero).execute()
        ingresos_oc = ingresos_response.data or []
        
        # Verificar si se puede eliminar (no tiene ingresos)
        puede_eliminar = len(ingresos_oc) == 0
        
        # Preparar líneas con formato
        lineas_formateadas = []
        for ln in lineas_oc:
            lineas_formateadas.append({
                "codigo": ln.get("codigo") or "",
                "descripcion": ln.get("descripcion") or "",
                "cantidad": safe_float(ln.get("cantidad")),
                "precio_unitario": safe_float(ln.get("precio_unitario")),
                "total": safe_float(ln.get("total")),
                "tipo": ln.get("tipo") or "",
                "art_corr": ln.get("art_corr") or ""
            })
        
        return jsonify({
            "success": True,
            "data": {
                "orden_compra": oc_numero,
                "proveedor": proveedor,
                "fecha": fecha_val,
                "lineas": lineas_formateadas,
                "puede_eliminar": puede_eliminar,
                "total_lineas": len(lineas_formateadas)
            }
        })
        
    except Exception as e:
        # Loguear traza completa para diagnosticar 500s
        current_app.logger.exception(f"Error en detalle_orden: {e}")
        return jsonify({
            "success": False,
            "message": f"Error al obtener detalle: {str(e)}"
        }), 500


@bp.route("/sacar-informe/<oc_numero>", methods=["POST"])
@token_required
def sacar_del_informe(current_user, oc_numero):
    """
    Marca una OC para que no aparezca en el informe (elimina_oc = ELIMINA_OC_FLAG)
    """
    try:
        supabase = current_app.config['SUPABASE']
        
        current_app.logger.info(f"Sacando OC {oc_numero} del informe")
        
        # Verificar que la OC existe
        check = supabase.table("orden_de_compra").select("orden_compra").eq("orden_compra", oc_numero).limit(1).execute()
        
        if not check.data:
            return jsonify({
                "success": False,
                "message": f"OC {oc_numero} no encontrada"
            }), 404
        
        # Actualizar todas las líneas de la OC usando el flag configurado
        result = supabase.table("orden_de_compra").update({
            "elimina_oc": ELIMINA_OC_FLAG
        }).eq("orden_compra", oc_numero).execute()
        
        updated_count = len(result.data) if result.data else 0
        
        current_app.logger.info(f"OC {oc_numero} sacada del informe. Registros actualizados: {updated_count}")
        
        return jsonify({
            "success": True,
            "message": f"OC {oc_numero} sacada del informe correctamente",
            "updated": updated_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en sacar_del_informe: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error al sacar del informe: {str(e)}"
        }), 500


@bp.route("/eliminar/<oc_numero>", methods=["DELETE"])
@token_required
def eliminar_orden(current_user, oc_numero):
    """
    Elimina completamente una OC (solo si no tiene ingresos asociados)
    """
    try:
        supabase = current_app.config['SUPABASE']
        
        current_app.logger.info(f"Intentando eliminar OC {oc_numero}")
        
        # Verificar que no tenga ingresos
        ingresos = supabase.table("ingresos").select("id").eq("orden_compra", oc_numero).limit(1).execute()
        
        if ingresos.data:
            return jsonify({
                "success": False,
                "message": "No se puede eliminar la OC porque tiene ingresos asociados"
            }), 400
        
        # Eliminar todas las líneas de la OC
        result = supabase.table("orden_de_compra").delete().eq("orden_compra", oc_numero).execute()
        
        deleted_count = len(result.data) if result.data else 0
        
        current_app.logger.info(f"OC {oc_numero} eliminada. Registros eliminados: {deleted_count}")
        
        return jsonify({
            "success": True,
            "message": f"OC {oc_numero} eliminada correctamente",
            "deleted": deleted_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en eliminar_orden: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error al eliminar: {str(e)}"
        }), 500


@bp.route("/diagnostics", methods=["GET"]) 
@token_required
def diagnostics(current_user):
    """Endpoint de diagnóstico para comparar counts y detectar discrepancias.

    Devuelve conteos de orden_de_compra e ingresos, top OCs por líneas y una
    muestra de OCs que el backend marca como pendientes según la lógica actual.
    """
    try:
        supabase = current_app.config['SUPABASE']

        # Obtener filas relevantes
        oc_rows = supabase.table("orden_de_compra").select(
            "orden_compra, total, art_corr, elimina_oc, proyecto"
        ).order("orden_compra", desc=True).execute().data or []

        ingresos_rows = supabase.table("ingresos").select("orden_compra, art_corr").execute().data or []

        # Filtrar no eliminadas usando la bandera configurada
        oc_rows_no_elim = [ln for ln in oc_rows if safe_str(ln.get("elimina_oc")) != ELIMINA_OC_FLAG]

        total_rows = len(oc_rows_no_elim)
        distinct_oc_set = {safe_str(ln.get("orden_compra")) for ln in oc_rows_no_elim if ln.get("orden_compra") is not None}
        total_distinct_oc = len(distinct_oc_set)

        distinct_ing_oc_set = {safe_str(i.get("orden_compra")) for i in ingresos_rows if i.get("orden_compra")}
        total_distinct_ing_oc = len(distinct_ing_oc_set)

        # Intersección
        inters = distinct_oc_set.intersection(distinct_ing_oc_set)
        inters_count = len(inters)

        # Top OCs por número de líneas y suma total
        oc_counter = Counter()
        oc_total = Counter()
        for ln in oc_rows_no_elim:
            oc = safe_str(ln.get("orden_compra"))
            oc_counter[oc] += 1
            try:
                oc_total[oc] += float(ln.get("total") or 0)
            except Exception:
                oc_total[oc] += 0

        top_ocs = []
        for oc, cnt in oc_counter.most_common(20):
            top_ocs.append({"orden_compra": oc, "lineas": cnt, "suma_total": oc_total.get(oc, 0)})

        # OCs pendientes según la lógica actual (replicar lista)
        ingresos_set = create_ingresos_set(ingresos_rows)

        oc_pendientes = {}
        for ln in oc_rows_no_elim:
            oc = safe_str(ln.get("orden_compra"))
            if not oc:
                continue
            proveedor = safe_str(ln.get("proveedor"))
            fecha = ln.get("fecha")
            monto_total = safe_float(ln.get("total"))

            # Evaluar por (oc, art_corr) - LÓGICA CORREGIDA
            art_corr = normalize_art_corr(ln.get("art_corr"))
            clave = (oc, art_corr)
            is_received = clave in ingresos_set

            # Si esta línea NO está recibida, agregar
            if not is_received:
                if oc not in oc_pendientes:
                    oc_pendientes[oc] = {"orden_compra": oc, "proveedor": proveedor, "fecha": fecha, "monto_total": 0.0}
                oc_pendientes[oc]["monto_total"] += monto_total

        pendientes_list = list(oc_pendientes.keys())[:50]

        return jsonify({
            "success": True,
            "total_rows_no_eliminadas": total_rows,
            "total_distinct_oc": total_distinct_oc,
            "total_ingresos_rows": len(ingresos_rows),
            "total_distinct_ing_oc": total_distinct_ing_oc,
            "intersect_oc_with_ingresos": inters_count,
            "top_ocs_by_lines": top_ocs,
            "sample_pending_ocs": pendientes_list
        })

    except Exception as e:
        current_app.logger.exception(f"Error en diagnostics: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/diagnostics-detailed", methods=["GET"]) 
@token_required
def diagnostics_detailed(current_user):
    """
    Diagnóstico detallado para encontrar la discrepancia
    """
    try:
        supabase = current_app.config['SUPABASE']

        # 1. Obtener TODAS las líneas sin filtrar
        all_oc_lines = supabase.table("orden_de_compra").select(
            "orden_compra, elimina_oc, art_corr"
        ).execute().data or []

        # 2. Analizar valores de elimina_oc
        elimina_oc_values = {}
        for ln in all_oc_lines:
            val = ln.get("elimina_oc")
            val_str = safe_str(val)
            if val_str not in elimina_oc_values:
                elimina_oc_values[val_str] = {"count": 0, "ocs": set()}
            elimina_oc_values[val_str]["count"] += 1
            elimina_oc_values[val_str]["ocs"].add(ln.get("orden_compra"))

        # Convertir sets a listas para JSON
        for key in elimina_oc_values:
            elimina_oc_values[key]["ocs"] = list(elimina_oc_values[key]["ocs"])
            elimina_oc_values[key]["total_ocs"] = len(elimina_oc_values[key]["ocs"])

        # 3. Obtener ingresos
        ingresos = supabase.table("ingresos").select("orden_compra, art_corr").execute().data or []
        ingresos_set = create_ingresos_set(ingresos)

        # 4. Filtrar con diferentes criterios
        filters_comparison = {}

        # Sin filtro de elimina_oc
        oc_lines_no_filter = all_oc_lines
        filters_comparison["sin_filtro"] = {
            "total_lineas": len(oc_lines_no_filter),
            "total_ocs": len(set(ln.get("orden_compra") for ln in oc_lines_no_filter))
        }

        # Filtro por "1"
        oc_lines_filter_1 = [ln for ln in all_oc_lines if safe_str(ln.get("elimina_oc")) != "1"]
        filters_comparison["filtro_1"] = {
            "total_lineas": len(oc_lines_filter_1),
            "total_ocs": len(set(ln.get("orden_compra") for ln in oc_lines_filter_1))
        }

        # Filtro por "SI"
        oc_lines_filter_SI = [ln for ln in all_oc_lines if safe_str(ln.get("elimina_oc")).upper() != "SI"]
        filters_comparison["filtro_SI"] = {
            "total_lineas": len(oc_lines_filter_SI),
            "total_ocs": len(set(ln.get("orden_compra") for ln in oc_lines_filter_SI))
        }

        # 5. Contar OCs pendientes con cada filtro - LÓGICA CORREGIDA
        def count_pending_ocs(lines):
            oc_pendientes = {}
            for ln in lines:
                oc = safe_str(ln.get("orden_compra"))
                if not oc:
                    continue
                art_corr = normalize_art_corr(ln.get("art_corr"))
                clave = (oc, art_corr)
                
                # Si esta línea NO está en ingresos, contarla
                if clave not in ingresos_set:
                    oc_pendientes[oc] = True
            
            return len(oc_pendientes)

        filters_comparison["sin_filtro"]["ocs_pendientes"] = count_pending_ocs(oc_lines_no_filter)
        filters_comparison["filtro_1"]["ocs_pendientes"] = count_pending_ocs(oc_lines_filter_1)
        filters_comparison["filtro_SI"]["ocs_pendientes"] = count_pending_ocs(oc_lines_filter_SI)

        return jsonify({
            "success": True,
            "elimina_oc_values_found": elimina_oc_values,
            "filters_comparison": filters_comparison,
            "total_ingresos": len(ingresos),
            "recommendation": "Usa el filtro que te da 31 OCs pendientes"
        })

    except Exception as e:
        current_app.logger.exception(f"Error en diagnostics_detailed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/diagnostics-lines", methods=["GET"]) 
@token_required
def diagnostics_lines(current_user):
    """
    Devuelve para una muestra de OCs pendientes (según filtro ELIMINA_OC_FLAG)
    las líneas de la OC con información de si cada línea tiene un ingreso
    coincidente (por (oc, art_corr)). También devuelve ingresos que no
    emparejan con ninguna línea (ingresos sin match) para facilitar debug.
    """
    try:
        supabase = current_app.config['SUPABASE']

        # Obtener todas las líneas no eliminadas
        oc_rows = supabase.table("orden_de_compra").select(
            "orden_compra, proveedor, fecha, total, art_corr, codigo, descripcion, cantidad, elimina_oc"
        ).order("orden_compra", desc=True).execute().data or []

        oc_rows = [ln for ln in oc_rows if safe_str(ln.get("elimina_oc")) != ELIMINA_OC_FLAG]

        # Obtener ingresos
        ingresos = supabase.table("ingresos").select("orden_compra, art_corr, id").execute().data or []
        ingresos_set = create_ingresos_set(ingresos)

        # Crear set de tuplas de líneas para comparación
        order_line_tuples = set()
        for ln in oc_rows:
            oc = safe_str(ln.get("orden_compra"))
            if not oc:
                continue
            art = normalize_art_corr(ln.get("art_corr"))
            order_line_tuples.add((oc, art))

        # Determinar OCs pendientes usando LÓGICA CORREGIDA
        # (al menos una línea sin ingreso)
        pending_ocs_set = set()
        for ln in oc_rows:
            oc = safe_str(ln.get("orden_compra"))
            if not oc:
                continue
            art = normalize_art_corr(ln.get("art_corr"))
            clave = (oc, art)
            if clave not in ingresos_set:
                pending_ocs_set.add(oc)

        pending_ocs = list(pending_ocs_set)

        # Tomar una muestra (limit)
        limit = 30
        sample_ocs = pending_ocs[:limit]

        # Construir detalle por OC
        sample_details = {}
        for oc in sample_ocs:
            lines = [ln for ln in oc_rows if safe_str(ln.get("orden_compra")) == oc]
            detalle = []
            for ln in lines:
                art_raw = ln.get("art_corr")
                art_norm = normalize_art_corr(art_raw)
                clave = (oc, art_norm)
                tiene_ingreso = clave in ingresos_set
                detalle.append({
                    "codigo": ln.get("codigo"),
                    "descripcion": ln.get("descripcion"),
                    "art_corr_raw": art_raw,
                    "art_corr_norm": art_norm,
                    "total_linea": safe_float(ln.get("total")),
                    "tiene_ingreso": bool(tiene_ingreso)
                })
            sample_details[oc] = detalle

        # Ingresos sin match con ninguna línea (posibles orfanos)
        ingresos_sin_match = []
        for ing in ingresos:
            oc = safe_str(ing.get("orden_compra"))
            art = normalize_art_corr(ing.get("art_corr"))
            if (oc, art) not in order_line_tuples:
                ingresos_sin_match.append({
                    "id": ing.get("id"),
                    "orden_compra": oc,
                    "art_corr_raw": ing.get("art_corr"),
                    "art_corr_norm": art
                })

        return jsonify({
            "success": True,
            "sample_count": len(sample_ocs),
            "sample_ocs": sample_ocs,
            "sample_details": sample_details,
            "ingresos_sin_match_count": len(ingresos_sin_match),
            "ingresos_sin_match": ingresos_sin_match[:200]
        })

    except Exception as e:
        current_app.logger.exception(f"Error en diagnostics_lines: {e}")
        return jsonify({"success": False, "message": str(e)}), 500