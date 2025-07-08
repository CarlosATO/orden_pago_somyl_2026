# app/modules/ingresos.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from datetime import date
from collections import defaultdict
from app.modules.usuarios import get_modulos_usuario

# 1) Definimos el Blueprint ANTES de usar @bp.route
bp = Blueprint("ingresos", __name__, template_folder="../templates/ingresos")


@bp.route("/", methods=["GET"])
def list_ingresos():
    if 'ingresos' not in get_modulos_usuario():
        flash('No tienes permiso para acceder a este módulo.', 'danger')
        return redirect(url_for('index'))

    supabase = current_app.config["SUPABASE"]
    oc = request.args.get("oc", type=int)

    # 0) Datalist de OC disponibles (solo números únicos, ordenados)
    oc_raw = (
        supabase.table("orden_de_compra")
                 .select("orden_compra")
                 .order("orden_compra")
                 .execute().data or []
    )
    oc_nums = sorted(set(int(oc["orden_compra"]) for oc in oc_raw if oc["orden_compra"] is not None))
    max_oc = max(oc_nums) if oc_nums else ""

    # Si no viene por querystring, usar el mayor por defecto
    if not oc:
        oc = max_oc

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
            header = {
                "orden_compra": od["orden_compra"],
                "fecha":        od["fecha"],
                "solicita":     od["solicita"],
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

            # 3) Líneas de la OC
            oc_lines = (
                supabase.table("orden_de_compra")
                         .select("codigo, descripcion, cantidad, precio_unitario, art_corr")
                         .eq("orden_compra", oc)
                         .execute().data or []
            )

            # 3a) Mapear descripciones a material_id
            descs = [ln["descripcion"] for ln in oc_lines]
            mats = (
                supabase.table("materiales")
                         .select("id, material")
                         .in_("material", descs)
                         .execute().data or []
            )
            mat_id_map = {m["material"]: m["id"] for m in mats}

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
                    "material_id":    mat_id_map.get(ln["descripcion"], None),
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
    guia         = f.get("guia_recepcion", "")
    # Ahora opcional: factura puede estar en form o no
    factura_val  = f.get("factura", None) or None

    # ADVERTENCIA si no hay número de documento
    if not guia:
        flash("Acaba de registrar un ingreso sin documento. Quedará pendiente en el módulo Doc Pendientes.", "warning")

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

    mats = (
        supabase.table("materiales")
                 .select("material, tipo, item")
                 .in_("material", descs)
                 .execute().data or []
    )
    mat_map = {m["material"]: m for m in mats}

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

        mat_id = int(mat_ids[idx] or 0)
        neto   = float(netos[idx] or 0)
        net_rec = rec * neto
        next_n += 1

        ocd = oc_map.get(desc, {})
        mat = mat_map.get(desc, {})

        tipo_id = tipo_to_id.get(mat.get("tipo"))
        fac_sin = 1 if ocd.get("fac_sin_iva") else 0

        to_insert.append({
            "orden_compra":    oc_val,
            "id_or_compra":    orden_id,
            "fecha":           hoy,
            "factura":         factura_val,
            "guia_recepcion":  guia,
            "material":        mat_id,
            "recepcion":       rec,
            "neto_unitario":   neto,
            "neto_recepcion":  net_rec,
            "art_corr":        art_corrs[idx],
            "fac_sin_iva":     fac_sin,
            "tipo":            tipo_id,
            "item":            mat.get("item"),
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
    # Busca OCs que contengan el término
    ocs = (
        supabase.table("orden_de_compra")
                 .select("orden_compra")
                 .ilike("orden_compra", f"%{term}%")
                 .order("orden_compra", desc=True)
                 .limit(20)
                 .execute().data or []
    )
    results = [{"id": oc["orden_compra"], "text": str(oc["orden_compra"])} for oc in ocs if oc.get("orden_compra")]
    return jsonify({"results": results})