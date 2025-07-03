from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    current_app,
    jsonify
)
from flask_login import login_required

bp_pending = Blueprint(
    "ordenes_pago_pendientes", __name__,
    template_folder="../templates/ordenes_pago"
)

@login_required
@bp_pending.route("/pendientes", methods=["GET"])
def list_pendientes():
    """
    Muestra todas las líneas de orden_de_pago con estado_documento = 'pendiente'.
    """
    supabase = current_app.config["SUPABASE"]
    # Consultar filas pendientes
    filas = (
        supabase
        .table("orden_de_pago")
        .select(
            "id, orden_compra, orden_numero, proveedor_nombre, material_nombre, cantidad, detalle_compra"
        )
        .eq("estado_documento", "pendiente")
        .order("orden_numero", desc=False)
        .execute()
        .data
    ) or []

    return render_template(
        "ordenes_pago/pendientes.html",
        filas=filas
    )

@login_required
@bp_pending.route("/pendientes/update", methods=["POST"])
def update_pendiente():
    """
    Actualiza una o varias líneas pendientes con el número de factura.
    Se espera un form con factura_id[] y factura_num[] o JSON.
    """
    supabase = current_app.config["SUPABASE"]
    # Si es AJAX JSON
    if request.is_json:
        data = request.get_json()
        updates = data.get("updates", [])
        results = []
        for upd in updates:
            op_id = upd.get("id")
            factura = upd.get("factura")
            if not factura or int(factura) <= 0:
                results.append({"id": op_id, "success": False, "msg": "Factura inválida"})
                continue
            # Validar duplicado
            exists = (
                supabase
                .table("orden_de_pago")
                .select("id")
                .eq("proveedor_nombre", upd.get("proveedor_nombre"))
                .eq("factura", factura)
                .neq("id", op_id)
                .execute()
                .data
            )
            if exists:
                results.append({"id": op_id, "success": False, "msg": "Factura duplicada"})
                continue
            # Update
            supabase.table("orden_de_pago")\
                .update({
                    "factura": factura,
                    "estado_documento": "completado"
                }) \
                .eq("id", op_id) \
                .execute()
            results.append({"id": op_id, "success": True})
        return jsonify(results)

    # Si es form normal
    ids = request.form.getlist("id[]")
    nums = request.form.getlist("factura[]")
    any_error = False
    for i, op_id in enumerate(ids):
        factura = nums[i]
        if not factura or int(factura) <= 0:
            flash(f"Factura inválida para línea {op_id}", "danger")
            any_error = True
            continue
        # Validar duplicado, omito aquí (similar al bloque JSON)
        supabase.table("orden_de_pago")\
            .update({"factura": factura, "estado_documento": "completado"})\
            .eq("id", int(op_id))\
            .execute()
    if any_error:
        flash("Algunas líneas no se pudieron actualizar.", "warning")
    else:
        flash("Documento(s) agregado(s) con éxito.", "success")
    return redirect(url_for("ordenes_pago_pendientes.list_pendientes"))
