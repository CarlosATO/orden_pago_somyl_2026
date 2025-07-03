# app/modules/trabajadores.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.modules.usuarios import require_modulo

bp = Blueprint("trabajadores", __name__, template_folder="../templates/trabajadores")

@bp.route("/", methods=["GET"])
@require_modulo('trabajadores')
def list_trabajadores():
    trabajadores = (
        current_app.config['SUPABASE']
        .table("trabajadores")
        .select("*")
        .execute()
        .data or []
    )
    return render_template("trabajadores/form.html", trabajadores=trabajadores)

@bp.route("/new", methods=["POST"])
@require_modulo('trabajadores')
def new_trabajador():
    nombre = request.form["nombre"].strip().upper()
    correo = request.form["correo"].strip().lower()

    # Verificar duplicado por correo
    dup = (
        current_app.config['SUPABASE']
        .table("trabajadores")
        .select("id")
        .eq("correo", correo)
        .execute()
        .data
    )
    if dup:
        flash("El correo ya está registrado.", "danger")
        return redirect(url_for("trabajadores.list_trabajadores"))

    payload = {
        "nombre": nombre,
        "correo": correo
    }
    current_app.config['SUPABASE'].table("trabajadores").insert(payload).execute()
    flash("Trabajador creado exitosamente.", "success")
    return redirect(url_for("trabajadores.list_trabajadores"))

@bp.route("/edit/<int:id>", methods=["GET", "POST"])
@require_modulo('trabajadores')
def edit_trabajador(id):
    res = (
        current_app.config['SUPABASE']
        .table("trabajadores")
        .select("*")
        .eq("id", id)
        .execute()
    )
    trabajador = (res.data or [None])[0]
    if not trabajador:
        flash("Trabajador no encontrado.", "danger")
        return redirect(url_for("trabajadores.list_trabajadores"))

    if request.method == "POST":
        nombre_new = request.form["nombre"].strip().upper()
        correo_new = request.form["correo"].strip().lower()

        if correo_new != trabajador["correo"]:
            dup = (
                current_app.config['SUPABASE']
                .table("trabajadores")
                .select("id")
                .eq("correo", correo_new)
                .execute()
                .data
            )
            if dup:
                flash("El correo ya está registrado.", "danger")
                trabajadores = (
                    current_app.config['SUPABASE']
                    .table("trabajadores")
                    .select("*")
                    .execute()
                    .data or []
                )
                return render_template(
                    "trabajadores/form.html",
                    trabajadores=trabajadores,
                    trabajador=trabajador
                )

        payload = {
            "nombre": nombre_new,
            "correo": correo_new
        }
        (
            current_app.config['SUPABASE']
            .table("trabajadores")
            .update(payload)
            .eq("id", id)
            .execute()
        )
        flash("Trabajador actualizado exitosamente.", "success")
        return redirect(url_for("trabajadores.list_trabajadores"))

    trabajadores = (
        current_app.config['SUPABASE']
        .table("trabajadores")
        .select("*")
        .execute()
        .data or []
    )
    return render_template(
        "trabajadores/form.html",
        trabajadores=trabajadores,
        trabajador=trabajador
    )