# app/modules/materiales.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.modules.usuarios import require_modulo

bp = Blueprint('materiales', __name__) 

def _get_items():
    """Helper: traer todos los tipos desde la tabla item, ordenados ascendente."""
    return (
        current_app.config['SUPABASE']
        .table("item")
        .select("tipo")
        .order("tipo", desc=False)
        .execute()
        .data or []
    )

@bp.route("/", methods=["GET"])
@require_modulo('materiales')
def list_materiales():
    materiales = (
        current_app.config['SUPABASE']
        .table("materiales")
        .select("*")
        .execute()
        .data or []
    )
    items = _get_items()
    return render_template("materiales/form.html",
                           materiales=materiales,
                           items=items,
                           material=None)

@bp.route("/new", methods=["POST"])
@require_modulo('materiales')
def new_material():
    cod      = request.form["cod"].strip().upper()
    material = request.form["material"].strip().upper()
    tipo     = request.form["tipo"].strip().upper()
    item     = request.form["item"].strip().upper()

    # Verificar duplicado de código
    existe = (
        current_app.config['SUPABASE']
        .table("materiales")
        .select("id")
        .eq("cod", cod)
        .execute()
        .data
    )
    if existe:
        flash("El código ya está registrado.", "danger")
        return redirect(url_for("materiales.list_materiales"))

    payload = {
        "cod":      cod,
        "material": material,
        "tipo":     tipo,
        "item":     item
    }
    current_app.config['SUPABASE'].table("materiales").insert(payload).execute()
    flash("Material creado exitosamente.", "success")
    return redirect(url_for("materiales.list_materiales"))

@bp.route("/edit/<int:id>", methods=["GET", "POST"])
@require_modulo('materiales')
def edit_material(id):
    # Obtener el material actual
    res = (
        current_app.config['SUPABASE']
        .table("materiales")
        .select("*")
        .eq("id", id)
        .execute()
    )
    mat = (res.data or [None])[0]
    if not mat:
        flash("Material no encontrado.", "danger")
        return redirect(url_for("materiales.list_materiales"))

    if request.method == "POST":
        cod_new      = request.form["cod"].strip().upper()
        material_new = request.form["material"].strip().upper()
        tipo_new     = request.form["tipo"].strip().upper()
        item_new     = request.form["item"].strip().upper()

        # Si cambió el código, verificar duplicado
        if cod_new != mat["cod"]:
            dup = (
                current_app.config['SUPABASE']
                .table("materiales")
                .select("id")
                .eq("cod", cod_new)
                .execute()
                .data
            )
            if dup:
                flash("El código ya está registrado.", "danger")
                materiales = (
                    current_app.config['SUPABASE']
                    .table("materiales")
                    .select("*")
                    .execute()
                    .data or []
                )
                items = _get_items()
                return render_template("materiales/form.html",
                                       materiales=materiales,
                                       material=mat,
                                       items=items)

        # Payload de actualización
        payload = {
            "cod":      cod_new,
            "material": material_new,
            "tipo":     tipo_new,
            "item":     item_new
        }
        (
            current_app.config['SUPABASE']
            .table("materiales")
            .update(payload)
            .eq("id", id)
            .execute()
        )
        flash("Material actualizado exitosamente.", "success")
        return redirect(url_for("materiales.list_materiales"))

    # GET: renderizar formulario con datos y lista
    materiales = (
        current_app.config['SUPABASE']
        .table("materiales")
        .select("*")
        .execute()
        .data or []
    )
    items = _get_items()
    return render_template("materiales/form.html",
                           materiales=materiales,
                           material=mat,
                           items=items)