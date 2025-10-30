import re
from datetime import date
from collections import defaultdict
from flask import Blueprint, request, jsonify, current_app

# ========= Importaciones de Utilidades =========
from backend.utils.decorators import token_required
from backend.utils.cache import cache_result

bp = Blueprint("ingresos", __name__)

# ========= Funciones Auxiliares =========

def normalize_text(text):
    """
    Normaliza texto para comparación: lowercase, sin espacios múltiples.
    """
    if not text:
        return ''
    return ' '.join(str(text).replace('\n', ' ').split()).lower()


# ================================================================
# ENDPOINT PRINCIPAL DE INGRESOS
# ================================================================

@bp.route("/", methods=["GET"])
@token_required
def get_ingresos_por_oc(current_user):
    """
    Obtiene los datos de una OC para registrar ingresos.
    Query params: oc (número de orden de compra)
    """
    supabase = current_app.config['SUPABASE']
    oc = request.args.get('oc', type=int)
    
    try:
        # 1. Obtener lista de OCs disponibles (ordenadas desc)
        oc_raw = (
            supabase.table("orden_de_compra")
            .select("orden_compra")
            .order("orden_compra", desc=True)
            .execute().data or []
        )
        oc_nums = sorted(set(int(oc_item["orden_compra"]) for oc_item in oc_raw if oc_item["orden_compra"] is not None), reverse=True)
        max_oc = oc_nums[0] if oc_nums else None
        
        # Si no viene OC, usar la más reciente
        if not oc and max_oc:
            oc = max_oc
        
        response_data = {
            "oc_list": oc_nums,
            "oc_seleccionada": oc,
            "header": {},
            "lineas": [],
            "oc_no_encontrada": False
        }
        
        if not oc:
            return jsonify({"success": True, "data": response_data})
        
        # 2. Obtener cabecera de la OC
        oc_res = (
            supabase.table("orden_de_compra")
            .select("orden_compra, proveedor, fecha, solicita, fac_sin_iva")
            .eq("orden_compra", oc)
            .limit(1)
            .execute().data or []
        )
        
        if not oc_res:
            response_data["oc_no_encontrada"] = True
            return jsonify({"success": True, "data": response_data})
        
        od = oc_res[0]
        
        # Obtener nombre del solicitante
        solicita_nombre = od["solicita"]
        if solicita_nombre and str(solicita_nombre).isdigit():
            trabajador = (
                supabase.table("trabajadores")
                .select("nombre")
                .eq("id", int(solicita_nombre))
                .limit(1)
                .execute().data or []
            )
            if trabajador:
                solicita_nombre = trabajador[0]["nombre"]
        
        # 3. Obtener datos del proveedor
        prov = (
            supabase.table("proveedores")
            .select("nombre, rut")
            .eq("id", od["proveedor"])
            .limit(1)
            .execute().data or []
        )
        
        response_data["header"] = {
            "orden_compra": od["orden_compra"],
            "fecha": od["fecha"],
            "solicita": solicita_nombre,
            "fac_sin_iva": bool(od["fac_sin_iva"]),
            "proveedor_id": od["proveedor"],
            "proveedor_nombre": prov[0]["nombre"] if prov else "",
            "rut": prov[0]["rut"] if prov else ""
        }
        
        # 4. Obtener líneas de la OC con paginación manual
        page_size = 1000
        offset = 0
        oc_lines = []
        while True:
            batch = (
                supabase.table("orden_de_compra")
                .select("codigo, descripcion, cantidad, precio_unitario, art_corr")
                .eq("orden_compra", oc)
                .range(offset, offset + page_size - 1)
                .execute().data or []
            )
            oc_lines.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        
        # 5. Mapear descripciones a material_id
        mats = (
            supabase.table("materiales")
            .select("id, material")
            .execute().data or []
        )
        mat_id_map = {normalize_text(m["material"]): m["id"] for m in mats}
        
        # 6. Obtener recepciones previas agrupadas por art_corr
        prev = (
            supabase.table("ingresos")
            .select("art_corr, recepcion")
            .eq("orden_compra", oc)
            .execute().data or []
        )
        ing_map = defaultdict(int)
        for i in prev:
            art = int(i["art_corr"])
            ing_map[art] += int(i["recepcion"] or 0)
        
        # 7. Construir líneas con cálculos
        for ln in oc_lines:
            sol = ln["cantidad"]
            net = float(ln["precio_unitario"] or 0)
            net_tot = sol * net
            total = net_tot if response_data["header"]["fac_sin_iva"] else net_tot * 1.19
            iva = total - net_tot
            
            art_key = int(ln["art_corr"])
            prev_r = ing_map.get(art_key, 0)
            pend = sol - prev_r
            
            # Buscar material_id normalizado
            norm_desc = normalize_text(ln["descripcion"])
            
            response_data["lineas"].append({
                "codigo": ln["codigo"],
                "descripcion": ln["descripcion"],
                "solicitado": sol,
                "neto": net,
                "neto_tot": net_tot,
                "iva": iva,
                "total": total,
                "total_recibido": prev_r,
                "pendiente": pend,
                "material_id": mat_id_map.get(norm_desc, None),
                "art_corr": ln["art_corr"],
            })
        
        return jsonify({"success": True, "data": response_data})
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener datos de ingreso para OC {oc}: {str(e)}")
        return jsonify({"success": False, "message": f"Error al obtener datos: {str(e)}"}), 500


@bp.route("/", methods=["POST"])
@token_required
def save_ingreso(current_user):
    """
    Guarda un nuevo ingreso de mercancía.
    """
    data = request.get_json()
    supabase = current_app.config['SUPABASE']
    
    try:
        # 1. Validar OC
        oc_val = data.get("oc")
        if not oc_val:
            return jsonify({"success": False, "message": "Orden de Compra inválida"}), 400
        
        try:
            oc_val = int(oc_val)
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Orden de Compra inválida"}), 400
        
        # 2. Obtener ID interno de OC
        oc_check = (
            supabase.table("orden_de_compra")
            .select("id")
            .eq("orden_compra", oc_val)
            .limit(1)
            .execute().data or []
        )
        
        if not oc_check:
            return jsonify({"success": False, "message": f"La Orden de Compra {oc_val} no existe"}), 404
        
        orden_id = oc_check[0]["id"]
        
        # 3. Validar datos del ingreso
        proveedor_id = data.get("proveedor_id")
        factura = (data.get("factura") or "").strip()
        guia = (data.get("guia_recepcion") or "").strip()
        lineas = data.get("lineas", [])
        fac_pendiente = data.get("fac_pendiente", False)
        
        if not proveedor_id:
            return jsonify({"success": False, "message": "Proveedor requerido"}), 400
        
        # 4. Validar factura duplicada (normalizada)
        if factura:
            factura_normalizada = normalize_text(factura)
            facturas_existentes = (
                supabase.table("ingresos")
                .select("factura")
                .eq("proveedor", proveedor_id)
                .execute().data or []
            )
            
            for fct in facturas_existentes:
                fct_val = normalize_text(fct.get("factura") or "")
                if fct_val and fct_val == factura_normalizada:
                    return jsonify({
                        "success": False, 
                        "message": f"La factura '{factura}' para este proveedor ya fue ingresada"
                    }), 400
        
        # 5. Calcular próximo n_ingreso
        last = (
            supabase.table("ingresos")
            .select("n_ingreso")
            .order("n_ingreso", desc=True)
            .limit(1)
            .execute().data or []
        )
        next_n = (last[0]["n_ingreso"] if last else 0)
        
        # 6. Obtener datos de OC para complementar
        oc_dt = (
            supabase.table("orden_de_compra")
            .select("descripcion, art_corr, fac_sin_iva")
            .eq("orden_compra", oc_val)
            .execute().data or []
        )
        oc_map = {d["descripcion"]: d for d in oc_dt}
        
        # Obtener materiales y tipos
        mats = (
            supabase.table("materiales")
            .select("id, material, tipo, item")
            .execute().data or []
        )
        mat_map = {normalize_text(m["material"]): m for m in mats}
        
        items = (
            supabase.table("item")
            .select("id, tipo")
            .execute().data or []
        )
        tipo_to_id = {it["tipo"]: it["id"] for it in items}
        
        hoy = date.today().isoformat()
        to_insert = []
        
        # 7. Procesar líneas
        for linea in lineas:
            rec = int(linea.get("recibido") or 0)
            if rec <= 0:
                continue
            
            desc = linea.get("descripcion", "")
            norm_desc = normalize_text(desc)
            mat = mat_map.get(norm_desc)
            
            # Validar material_id
            raw_mat_id = linea.get("material_id")
            if not raw_mat_id and mat:
                raw_mat_id = mat.get("id")
            
            if not raw_mat_id or raw_mat_id in (None, '', 'None'):
                return jsonify({
                    "success": False,
                    "message": f"No se encontró material_id para: '{desc}'. Verifique que el material existe en la base de datos."
                }), 400
            
            mat_id = int(raw_mat_id)
            neto = float(linea.get("neto") or 0)
            net_rec = rec * neto
            next_n += 1
            
            ocd = oc_map.get(desc, {})
            tipo_id = tipo_to_id.get(mat.get("tipo")) if mat else None
            fac_sin = 1 if ocd.get("fac_sin_iva") else 0
            
            insert_data = {
                "orden_compra": oc_val,
                "id_or_compra": orden_id,
                "fecha": hoy,
                "factura": factura,
                "guia_recepcion": guia,
                "material": mat_id,
                "recepcion": rec,
                "neto_unitario": neto,
                "neto_recepcion": net_rec,
                "art_corr": linea.get("art_corr"),
                "fac_sin_iva": fac_sin,
                "tipo": tipo_id,
                "item": mat.get("item") if mat else None,
                "proveedor": proveedor_id,
                "n_ingreso": next_n
            }
            
            if fac_pendiente:
                insert_data["fac_pendiente"] = '1'
            
            to_insert.append(insert_data)
        
        # 8. Insertar en 'ingresos'
        if not to_insert:
            return jsonify({"success": False, "message": "No se ingresó ningún registro válido"}), 400
        
        res = supabase.table("ingresos").insert(to_insert).execute()
        
        if res.data:
            # Mensaje de advertencia si no hay factura
            warning = None
            if not factura:
                warning = "Ingreso registrado sin número de factura. Quedará pendiente en Doc Pendientes."
            
            return jsonify({
                "success": True,
                "message": "Ingreso registrado con éxito",
                "warning": warning,
                "n_ingresos": len(res.data)
            })
        else:
            return jsonify({"success": False, "message": "Error al guardar ingreso"}), 500
        
    except Exception as e:
        current_app.logger.error(f"Error al guardar ingreso: {str(e)}")
        return jsonify({"success": False, "message": f"Error interno: {str(e)}"}), 500


# ================================================================
# ENDPOINTS AUXILIARES
# ================================================================

@bp.route("/api/buscar_oc", methods=["GET"])
@token_required
def api_buscar_oc(current_user):
    """
    Búsqueda de OCs para Select2/react-select.
    """
    supabase = current_app.config['SUPABASE']
    term = request.args.get("term", "").strip()
    
    if not term:
        return jsonify({"results": []})
    
    try:
        ocs = (
            supabase.table("orden_de_compra")
            .select("orden_compra")
            .ilike("orden_compra::text", f"%{term}%")
            .order("orden_compra", desc=True)
            .limit(20)
            .execute().data or []
        )
        
        # Eliminar duplicados
        oc_nums = sorted(set(oc["orden_compra"] for oc in ocs if oc.get("orden_compra")), reverse=True)
        results = [{"value": oc, "label": str(oc)} for oc in oc_nums]
        
        return jsonify({"results": results})
        
    except Exception as e:
        current_app.logger.error(f"Error en api_buscar_oc: {e}")
        return jsonify({"results": [], "error": "Error interno"}), 500


@bp.route("/historial/<int:oc_numero>", methods=["GET"])
@token_required
# @cache_result(ttl_seconds=120)  # Cache comentado: causa error de serialización con User
def get_historial_ingresos(current_user, oc_numero):
    """
    Obtiene el historial de ingresos de una OC específica.
    """
    supabase = current_app.config['SUPABASE']
    
    try:
        ingresos = (
            supabase.table("ingresos")
            .select("*, materiales(material)")
            .eq("orden_compra", oc_numero)
            .order("fecha", desc=True)
            .execute().data or []
        )
        
        historial = []
        for ing in ingresos:
            historial.append({
                "n_ingreso": ing.get("n_ingreso"),
                "fecha": ing.get("fecha"),
                "factura": ing.get("factura"),
                "guia_recepcion": ing.get("guia_recepcion"),
                "material": ing.get("materiales", {}).get("material") if ing.get("materiales") else "",
                "cantidad": ing.get("recepcion"),
                "neto_unitario": ing.get("neto_unitario"),
                "neto_recepcion": ing.get("neto_recepcion"),
                "fac_pendiente": ing.get("fac_pendiente") == '1'
            })
        
        return jsonify({"success": True, "data": historial})
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener historial de OC {oc_numero}: {str(e)}")
        return jsonify({"success": False, "message": "Error al obtener historial"}), 500