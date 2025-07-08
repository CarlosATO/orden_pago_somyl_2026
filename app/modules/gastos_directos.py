from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from app.modules.usuarios import require_modulo
from app.utils.static_data import get_cached_proyectos_with_id, get_cached_items_with_id
from datetime import date

bp_gastos_directos = Blueprint("gastos_directos", __name__, url_prefix="/gastos_directos")

@bp_gastos_directos.route("/", methods=["GET"])
@login_required
@require_modulo('gastos_directos')
def form_gastos_directos():
    supabase = current_app.config["SUPABASE"]
    
    # Usar datos cacheados para mejorar performance
    proyectos = get_cached_proyectos_with_id()
    items = get_cached_items_with_id()
    
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    return render_template(
        "gastos_directos.html",
        proyectos=proyectos,
        items=items,
        meses=meses,
        hoy=date.today()
    )

@bp_gastos_directos.route("/guardar", methods=["POST"])
@login_required
@require_modulo('gastos_directos')
def guardar_gastos_directos():
    supabase = current_app.config["SUPABASE"]
    data = request.get_json()
    gastos = data.get("gastos", [])
    proyecto_id = data.get("proyecto_id")
    usuario_id = current_user.id

    errores = []
    for gasto in gastos:
        try:
            supabase.table("gastos_directos").insert({
                "fecha": date.today().isoformat(),
                "proyecto_id": int(proyecto_id),
                "item_id": int(gasto["item_id"]),
                "descripcion": gasto["descripcion"],
                "mes": gasto["mes"],
                "monto": int(gasto["monto"]),
                "usuario_id": usuario_id
            }).execute()
        except Exception as e:
            errores.append(str(e))

    if errores:
        return jsonify(success=False, message="Algunos gastos no se guardaron: " + "; ".join(errores))
    return jsonify(success=True, message="Gastos guardados correctamente.")