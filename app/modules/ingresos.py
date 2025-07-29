# app/modules/ingresos.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from datetime import date
from collections import defaultdict
from app.modules.usuarios import get_modulos_usuario
from app.utils.cache import get_select2_cached_results, cache_select2_results

# 1) Definimos el Blueprint ANTES de usar @bp.route
bp = Blueprint("ingresos", __name__, template_folder="../templates/ingresos")


@bp.route("/", methods=["GET"])
def list_ingresos():
    # Normalizar nombres de módulos para comparación robusta
    modulos_usuario = [m.strip().lower() for m in get_modulos_usuario()]
    if 'ingresos' not in modulos_usuario:
        return render_template('sin_permisos.html')

    supabase = current_app.config["SUPABASE"]
    oc = request.args.get("oc", type=int)

    # 0) Datalist de OC disponibles (solo números únicos, ordenados)
    oc_raw = (
        supabase.table("orden_de_compra")
                 .select("orden_compra")
                 .order("orden_compra", desc=True)  # Ordenar descendente para obtener la última primero
                 .execute().data or []
    )
    oc_nums = sorted(set(int(oc["orden_compra"]) for oc in oc_raw if oc["orden_compra"] is not None), reverse=True)
    max_oc = oc_nums[0] if oc_nums else None

    # Si no viene por querystring, usar la OC más reciente por defecto
    if not oc and max_oc:
        oc = max_oc
        # Redirigir para que la URL muestre la OC seleccionada
        return redirect(url_for("ingresos.list_ingresos", oc=oc))

    header = {}
    lines = []

    if oc:
        # 1) Cabecera de la OC
        oc_res = (
            supabase.table("orden_de_compra")
                     .select("orden_compra, proveedor, fecha, solicita, fac_sin_iva")
                     .eq("orden_compra", oc)
                     .limit(1)
                     .execute().data or []
        )
        od = oc_res[0] if oc_res else None

        if od:
            # Obtener el nombre del solicitante si viene como ID
            solicita_nombre = od["solicita"]
            if solicita_nombre and solicita_nombre.isdigit():
                # Si es un número, buscar el nombre en la tabla trabajadores
                trabajador = (
                    supabase.table("trabajadores")
                             .select("nombre")
                             .eq("id", int(solicita_nombre))
                             .limit(1)
                             .execute().data or []
                )
                if trabajador:
                    solicita_nombre = trabajador[0]["nombre"]
            
            header = {
                "orden_compra": od["orden_compra"],
                "fecha":        od["fecha"],
                "solicita":     solicita_nombre,
                "fac_sin_iva":  bool(od["fac_sin_iva"]),
                "proveedor_id": od["proveedor"],
            }

            # 2) Nombre y RUT del proveedor
            prov = (
                supabase.table("proveedores")
                         .select("nombre, rut")
                         .eq("id", od["proveedor"])
                         .limit(1)
                         .execute().data or []
            )
            if prov:
                header["proveedor_nombre"] = prov[0]["nombre"]
                header["rut"]              = prov[0]["rut"]

            # 3) Líneas de la OC con paginación manual
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

            # 3a) Mapear descripciones a material_id (ignorando espacios y mayúsculas)
            descs = [ln["descripcion"] for ln in oc_lines]
            # Traer todos los materiales para comparación robusta
            mats = (
                supabase.table("materiales")
                         .select("id, material")
                         .execute().data or []
            )
            # Diccionario: clave normalizada -> id
            def norm(s):
                return (s or '').strip().lower()
            mat_id_map = {norm(m["material"]): m["id"] for m in mats}

            # 4) Recepciones previas agrupadas por art_corr
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

            # 5) Construir líneas con totales y pendientes
            for ln in oc_lines:
                sol     = ln["cantidad"]
                net     = float(ln["precio_unitario"] or 0)
                net_tot = sol * net
                total   = net_tot if header["fac_sin_iva"] else net_tot * 1.19
                iva     = total - net_tot

                art_key = int(ln["art_corr"])
                prev_r  = ing_map.get(art_key, 0)
                pend    = sol - prev_r

                # Normalizar descripción para buscar material_id
                norm_desc = (ln["descripcion"] or '').strip().lower()
                lines.append({
                    "codigo":         ln["codigo"],
                    "descripcion":    ln["descripcion"],
                    "solicitado":     sol,
                    "neto":           net,
                    "neto_tot":       net_tot,
                    "iva":            iva,
                    "total":          total,
                    "total_recibido": prev_r,
                    "pendiente":      pend,
                    "material_id":    mat_id_map.get(norm_desc, None),
                    "art_corr":       ln["art_corr"],
                })

    oc_no_encontrada = False

    # Si el usuario buscó una OC específica y no hay header ni lines, mostrar advertencia
    if request.args.get("oc") and not header:
        oc_no_encontrada = True

    return render_template(
        "ingresos/form.html",
        oc_list=oc_nums,
        oc=oc,
        header=header,
        lines=lines,
        oc_no_encontrada=oc_no_encontrada
    )


@bp.route("/", methods=["POST"], endpoint="save_ingresos")
def save_ingresos():
    if 'ingresos' not in get_modulos_usuario():
        flash('No tienes permiso para acceder a este módulo.', 'danger')
        return redirect(url_for('index'))

    supabase = current_app.config["SUPABASE"]
    f = request.form

    # 1) Validar número de OC
    raw_oc = f.get("oc", "")
    try:
        oc_val = int(raw_oc)
    except (ValueError, TypeError):
        flash("Orden de Compra inválida.", "danger")
        return redirect(url_for("ingresos.list_ingresos"))

    # 2) Obtener ID interno de OC
    oc_check = (
        supabase.table("orden_de_compra")
                 .select("id")
                 .eq("orden_compra", oc_val)
                 .limit(1)
                 .execute().data or []
    )
    if not oc_check:
        flash(f"La Orden de Compra {oc_val} no existe.", "warning")
        return redirect(url_for("ingresos.list_ingresos"))

    orden_id = oc_check[0]["id"]

    # 3) Leer datos del formulario
    proveedor_id = int(f.get("proveedor_id", 0))
    factura      = f.get("factura", "")  # Documento principal (factura)
    guia         = f.get("guia_recepcion", "")  # Guía de recepción (opcional)
    
    # ADVERTENCIA si no hay número de documento
    if not factura:
        flash("Acaba de registrar un ingreso sin número de factura. Quedará pendiente en el módulo Doc Pendientes.", "warning")

    descs        = f.getlist("desc_linea[]")
    mat_ids      = f.getlist("material_id[]")
    netos        = f.getlist("neto_linea[]")
    recs         = f.getlist("recibido_linea[]")
    art_corrs    = f.getlist("art_corr_linea[]")

    # 4) Calcular próximo n_ingreso
    last = (
        supabase.table("ingresos")
                 .select("n_ingreso")
                 .order("n_ingreso", desc=True)
                 .limit(1)
                 .execute().data or []
    )
    next_n = last[0]["n_ingreso"] if last else 0

    # 5) Datos auxiliares
    oc_dt = (
        supabase.table("orden_de_compra")
                 .select("descripcion, art_corr, fac_sin_iva")
                 .eq("orden_compra", oc_val)
                 .execute().data or []
    )
    oc_map = {d["descripcion"]: d for d in oc_dt}

    # Traer todos los materiales para comparación robusta
    mats = (
        supabase.table("materiales")
                 .select("material, tipo, item")
                 .execute().data or []
    )
    def norm(s):
        return (s or '').strip().lower()
    mat_map = {norm(m["material"]): m for m in mats}

    # DEBUG: Mostrar descripciones buscadas y encontradas
    import sys, logging
    try:
        print("--- DEBUG INGRESOS ---", flush=True)
        print("Descripciones buscadas (del formulario):", flush=True)
        for d in descs:
            print(f"- '{d}'", flush=True)
        print("Descripciones en la tabla materiales:", flush=True)
        for m in mats:
            print(f"- '{m['material']}'", flush=True)
        print("----------------------", flush=True)
    except Exception as e:
        logging.warning(f"DEBUG INGRESOS: {e}")

    items = (
        supabase.table("item")
                 .select("id, tipo")
                 .execute().data or []
    )
    tipo_to_id = {it["tipo"]: it["id"] for it in items}

    hoy = date.today().isoformat()
    to_insert = []

    # 6) Construir inserts
    for idx, desc in enumerate(descs):
        rec = int(recs[idx] or 0)
        if rec <= 0:
            continue

        # Buscar material normalizando descripción
        norm_desc = (desc or '').strip().lower()
        mat = mat_map.get(norm_desc)
        raw_mat_id = mat["id"] if mat and "id" in mat else mat_ids[idx]
        if raw_mat_id in (None, '', 'None'):
            desc_falla = descs[idx] if idx < len(descs) else '(desconocido)'
            try:
                print(f"[DEBUG] No se encontró material_id para: '{desc_falla}'", flush=True)
            except Exception as e:
                logging.warning(f"DEBUG INGRESOS: {e}")
            flash(f"No se encontró material_id para la descripción: '{desc_falla}'. Por favor verifique que el material exista en la base de datos o contacte a soporte.", "warning")
            return redirect(url_for("ingresos.list_ingresos", oc=oc_val))
        mat_id = int(raw_mat_id)
        neto   = float(netos[idx] or 0)
        net_rec = rec * neto
        next_n += 1

        ocd = oc_map.get(desc, {})
        tipo_id = tipo_to_id.get(mat.get("tipo")) if mat else None
        fac_sin = 1 if ocd.get("fac_sin_iva") else 0

        to_insert.append({
            "orden_compra":    oc_val,
            "id_or_compra":    orden_id,
            "fecha":           hoy,
            "factura":         factura,  # Documento principal
            "guia_recepcion":  guia,     # Guía de recepción (opcional)
            "material":        mat_id,
            "recepcion":       rec,
            "neto_unitario":   neto,
            "neto_recepcion":  net_rec,
            "art_corr":        art_corrs[idx],
            "fac_sin_iva":     fac_sin,
            "tipo":            tipo_id,
            "item":            mat.get("item") if mat else None,
            "proveedor":       proveedor_id,
            "n_ingreso":       next_n
        })

    # 7) Insertar en 'ingresos'
    if to_insert:
        res = supabase.table("ingresos").insert(to_insert).execute()
        if getattr(res, "error", None):
            flash(f"Error al guardar ingreso: {res.error}", "danger")
        else:
            flash("Ingreso registrado con éxito.", "success")
    else:
        flash("No se ingresó ningún registro.", "warning")

    return redirect(url_for("ingresos.list_ingresos", oc=oc_val))


@bp.route("/api/buscar_oc")
def api_buscar_oc():
    supabase = current_app.config["SUPABASE"]
    term = request.args.get("term", "")
    if not term:
        return jsonify({"results": []})
    
    # Intentar cache primero
    cached_results = get_select2_cached_results("orden_compra", term)
    if cached_results is not None:
        return jsonify({"results": cached_results})
    
    try:
        # Busca OCs que contengan el término - optimizado
        ocs = (
            supabase.table("orden_de_compra")
                     .select("orden_compra")
                     .ilike("orden_compra", f"%{term}%")
                     .order("orden_compra", desc=True)
                     .limit(20)
                     .execute().data or []
        )
        
        results = [{"id": oc["orden_compra"], "text": str(oc["orden_compra"])} for oc in ocs if oc.get("orden_compra")]
        
        # Cachear resultados
        if results:
            cache_select2_results("orden_compra", term, results)
        
        return jsonify({"results": results})
        
    except Exception as e:
        current_app.logger.error(f"Error en api_buscar_oc: {e}")
        return jsonify({"results": [], "error": "Error interno"}), 500