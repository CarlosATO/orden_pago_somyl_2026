# app/modules/items.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.modules.usuarios import require_modulo

bp = Blueprint("items", __name__, template_folder="../templates/items")

@bp.route("/", methods=["GET"])
@require_modulo('items')
def list_items():
    items = (
        current_app.config['SUPABASE']
        .table("item")
        .select("*")
        .order("tipo", desc=False)   # <-- Usar desc=False para ascendente
        .execute()
        .data or []
    )
    return render_template("items/form.html", items=items)

@bp.route("/new", methods=["POST"])
@require_modulo('items')
def new_item():
    tipo = request.form["tipo"].strip().upper()

    dup = (
        current_app.config['SUPABASE']
        .table("item")
        .select("id")
        .eq("tipo", tipo)
        .execute()
        .data
    )
    if dup:
        flash("Este tipo ya está registrado.", "danger")
        return redirect(url_for("items.list_items"))

    current_app.config['SUPABASE'].table("item").insert({"tipo": tipo}).execute()
    flash("Tipo creado exitosamente.", "success")
    # Invalidar cache de items para búsquedas (Select2)
    from app.utils.cache import invalidate_select2_cache
    invalidate_select2_cache("items")
    return redirect(url_for("items.list_items"))

@bp.route("/edit/<int:id>", methods=["GET", "POST"])
@require_modulo('items')
def edit_item(id):
    res = (
        current_app.config['SUPABASE']
        .table("item")
        .select("*")
        .eq("id", id)
        .execute()
    )
    item = (res.data or [None])[0]
    if not item:
        flash("Tipo no encontrado.", "danger")
        return redirect(url_for("items.list_items"))

    if request.method == "POST":
        tipo_new = request.form["tipo"].strip().upper()

        if tipo_new != item["tipo"]:
            dup = (
                current_app.config['SUPABASE']
                .table("item")
                .select("id")
                .eq("tipo", tipo_new)
                .execute()
                .data
            )
            if dup:
                flash("Este tipo ya está registrado.", "danger")
                items = (
                    current_app.config['SUPABASE']
                    .table("item")
                    .select("*")
                    .order("tipo", desc=False)
                    .execute()
                    .data or []
                )
                return render_template("items/form.html", items=items, item=item)

        current_app.config['SUPABASE'] \
            .table("item") \
            .update({"tipo": tipo_new}) \
            .eq("id", id) \
            .execute()
        flash("Tipo actualizado exitosamente.", "success")
        return redirect(url_for("items.list_items"))

    items = (
        current_app.config['SUPABASE']
        .table("item")
        .select("*")
        .order("tipo", desc=False)
        .execute()
        .data or []
    )
    return render_template("items/form.html", items=items, item=item)