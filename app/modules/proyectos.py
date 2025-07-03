# app/modules/proyectos.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.modules.usuarios import require_modulo

bp = Blueprint("proyectos", __name__, template_folder="../templates/proyectos")

@bp.route("/", methods=["GET"])
@require_modulo('proyectos')
def list_proyectos():
    proyectos = (
        current_app.config['SUPABASE']
        .table("proyectos")
        .select("*")
        .execute()
        .data or []
    )
    return render_template("proyectos/form.html", proyectos=proyectos)

@bp.route("/new", methods=["POST"])
@require_modulo('proyectos')
def new_proyecto():
    proyecto_val   = request.form["proyecto"].strip().upper()
    venta_val      = request.form["venta"].strip().upper()
    observacion_val= request.form["observacion"].strip().upper()

    # Verificar duplicado en columna 'proyecto'
    dup = (
        current_app.config['SUPABASE']
        .table("proyectos")
        .select("id")
        .eq("proyecto", proyecto_val)
        .execute()
        .data
    )
    if dup:
        flash("El proyecto ya existe.", "danger")
        return redirect(url_for("proyectos.list_proyectos"))

    payload = {
        "proyecto":    proyecto_val,
        "venta":       venta_val,
        "observacion": observacion_val
    }
    current_app.config['SUPABASE'].table("proyectos").insert(payload).execute()
    flash("Proyecto creado exitosamente.", "success")
    return redirect(url_for("proyectos.list_proyectos"))

@bp.route("/edit/<int:id>", methods=["GET", "POST"])
@require_modulo('proyectos')
def edit_proyecto(id):
    res = (
        current_app.config['SUPABASE']
        .table("proyectos")
        .select("*")
        .eq("id", id)
        .execute()
    )
    proyecto = (res.data or [None])[0]
    if not proyecto:
        flash("Proyecto no encontrado.", "danger")
        return redirect(url_for("proyectos.list_proyectos"))

    if request.method == "POST":
        nuevos = {
            "proyecto":    request.form["proyecto"].strip().upper(),
            "venta":       request.form["venta"].strip().upper(),
            "observacion": request.form["observacion"].strip().upper()
        }

        if nuevos["proyecto"] != proyecto["proyecto"]:
            dup = (
                current_app.config['SUPABASE']
                .table("proyectos")
                .select("id")
                .eq("proyecto", nuevos["proyecto"])
                .execute()
                .data
            )
            if dup:
                flash("El proyecto ya existe.", "danger")
                proyectos = (
                    current_app.config['SUPABASE']
                    .table("proyectos")
                    .select("*")
                    .execute()
                    .data or []
                )
                return render_template("proyectos/form.html",
                                       proyectos=proyectos,
                                       proyecto=proyecto)

        (
            current_app.config['SUPABASE']
            .table("proyectos")
            .update(nuevos)
            .eq("id", id)
            .execute()
        )
        flash("Proyecto actualizado exitosamente.", "success")
        return redirect(url_for("proyectos.list_proyectos"))

    proyectos = (
        current_app.config['SUPABASE']
        .table("proyectos")
        .select("*")
        .execute()
        .data or []
    )
    return render_template("proyectos/form.html",
                           proyectos=proyectos,
                           proyecto=proyecto)