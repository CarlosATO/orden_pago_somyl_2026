from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.modules.usuarios import require_modulo

bp = Blueprint("proveedores", __name__, template_folder="../templates/proveedores")

@bp.route("/", methods=["GET"])
@require_modulo('proveedores')
def list_proveedores():
    proveedores = current_app.config['SUPABASE'] \
        .table("proveedores") \
        .select("*") \
        .execute() \
        .data or []
    return render_template("proveedores/form.html", proveedores=proveedores)

@bp.route("/new", methods=["POST"])
@require_modulo('proveedores')
def new_proveedor():
    # Capturar y normalizar
    rut = request.form["rut"].upper().strip()
    # Verificar duplicado
    existente = current_app.config['SUPABASE'] \
        .table("proveedores") \
        .select("id") \
        .eq("rut", rut) \
        .execute() \
        .data
    if existente:
        flash("El RUT ya está registrado.", "danger")
        return redirect(url_for("proveedores.list_proveedores"))

    # Armar payload
    payload = {
        "nombre":     request.form["nombre"].strip().upper(),
        "rut":        rut,
        "direccion":  request.form["direccion"].strip().upper(),
        "comuna":     request.form["comuna"].strip().upper(),
        "fono":       request.form["fono"].strip().upper(),
        "contacto":   request.form["contacto"].strip().upper(),
        "correo":     request.form["correo"].strip(),
        "banco":      request.form["banco"].strip().upper(),
        "cuenta":     request.form["cuenta"].strip().upper(),
        "paguese_a":  request.form["paguese_a"].strip().upper()
    }
    # Insertar
    current_app.config['SUPABASE'].table("proveedores").insert(payload).execute()
    flash("Proveedor creado exitosamente.", "success")
    return redirect(url_for("proveedores.list_proveedores"))

@bp.route("/edit/<int:id>", methods=["GET", "POST"])
@require_modulo('proveedores')
def edit_proveedor(id):
    # Obtener proveedor actual
    res = current_app.config['SUPABASE'] \
        .table("proveedores") \
        .select("*") \
        .eq("id", id) \
        .execute()
    proveedor = (res.data or [None])[0]
    if not proveedor:
        flash("Proveedor no encontrado.", "danger")
        return redirect(url_for("proveedores.list_proveedores"))

    if request.method == "POST":
        rut = request.form["rut"].upper().strip()
        # Si cambió el RUT, verificar duplicado
        if rut != proveedor["rut"]:
            existe = current_app.config['SUPABASE'] \
                .table("proveedores") \
                .select("id") \
                .eq("rut", rut) \
                .execute() \
                .data
            if existe:
                flash("El RUT ya está registrado.", "danger")
                # volver al formulario con lista y datos
                proveedores = current_app.config['SUPABASE'] \
                    .table("proveedores") \
                    .select("*") \
                    .execute() \
                    .data or []
                return render_template(
                    "proveedores/form.html",
                    proveedores=proveedores,
                    proveedor=proveedor
                )

        # Armar payload de actualización
        payload = {
            "nombre":     request.form["nombre"].strip().upper(),
            "rut":        rut,
            "direccion":  request.form["direccion"].strip().upper(),
            "comuna":     request.form["comuna"].strip().upper(),
            "fono":       request.form["fono"].strip().upper(),
            "contacto":   request.form["contacto"].strip().upper(),
            "correo":     request.form["correo"].strip(),
            "banco":      request.form["banco"].strip().upper(),
            "cuenta":     request.form["cuenta"].strip().upper(),
            "paguese_a":  request.form["paguese_a"].strip().upper()
        }
        # Actualizar
        current_app.config['SUPABASE'] \
            .table("proveedores") \
            .update(payload) \
            .eq("id", id) \
            .execute()
        flash("Proveedor actualizado exitosamente.", "success")
        return redirect(url_for("proveedores.list_proveedores"))

    # GET: render con datos y lista
    proveedores = current_app.config['SUPABASE'] \
        .table("proveedores") \
        .select("*") \
        .execute() \
        .data or []
    return render_template(
        "proveedores/form.html",
        proveedores=proveedores,
        proveedor=proveedor
    )