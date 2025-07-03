from flask import (
    Blueprint, render_template, request,
    flash, redirect, url_for, current_app,
    send_file
)
from datetime import date, datetime, timedelta
from flask_login import login_required
import io
from openpyxl import Workbook
from app.modules.usuarios import require_modulo

bp_pagos = Blueprint(
    "pagos", __name__,
    template_folder="../templates"
)

def get_pagos(filtros=None):
    supabase = current_app.config["SUPABASE"]
    # Trae y agrupa igual que la vista
    all_rows = supabase \
        .table("orden_de_pago") \
        .select(
            "orden_numero, fecha, proveedor_nombre, detalle_compra, factura, "
            "costo_final_con_iva, proyecto, orden_compra, condicion_pago, vencimiento, fecha_factura"
        ) \
        .order("orden_numero") \
        .execute() \
        .data or []

    # Aplicar filtros si corresponde (aquí puedes adaptar según tus filtros)
    if filtros:
        # Ejemplo filtro: solo pagos de un proveedor
        if filtros.get("proveedor"):
            all_rows = [r for r in all_rows if r["proveedor_nombre"] == filtros["proveedor"]]

    # Agrupar por orden_numero
    pagos = {}
    for r in all_rows:
        num = r["orden_numero"]
        if num not in pagos:
            pagos[num] = {
                "orden_numero": num,
                "fecha": r["fecha"],
                "proveedor_nombre": r["proveedor_nombre"],
                "detalle_compra": r["detalle_compra"],
                "factura": r["factura"],
                "total_pago": 0.0,
                "proyecto": r["proyecto"],
                "orden_compra": r["orden_compra"],
                "condicion_pago": r["condicion_pago"],
                "vencimiento": r["vencimiento"],
                "fecha_factura": r["fecha_factura"],
                "fecha_pago": None
            }
        pagos[num]["total_pago"] += float(r.get("costo_final_con_iva") or 0)

    # Fechas de pago existentes
    pagos_guardados = (
        supabase
        .table("fechas_de_pagos_op")
        .select("orden_numero, fecha_pago")
        .execute()
        .data or []
    )
    fecha_map = {p["orden_numero"]: p["fecha_pago"] for p in pagos_guardados}
    for num, data in pagos.items():
        data["fecha_pago"] = fecha_map.get(num)

    # Cuentas corrientes de proveedores
    provs = supabase.table("proveedores").select("nombre, cuenta").execute().data or []
    cuenta_map = {p["nombre"]: p["cuenta"] for p in provs}
    for data in pagos.values():
        data["cuenta"] = cuenta_map.get(data["proveedor_nombre"], "")

    # Nombres de proyectos
    projs = supabase.table("proyectos").select("id, proyecto").execute().data or []
    proyecto_map = {pr["id"]: pr["proyecto"] for pr in projs}
    for data in pagos.values():
        proj_id = data.get("proyecto")
        data["proyecto"] = proyecto_map.get(proj_id, proj_id)

    # Retorna una lista ordenada igual que la tabla
    return list(pagos.values())

@login_required
@bp_pagos.route("/pagos", methods=["GET"])
@require_modulo('pagos')
def list_pagos():
    # Si hay filtros, recógelos aquí (adaptar según tus parámetros de filtro)
    filtros = {}
    # Ejemplo: filtro por proveedor desde GET
    proveedor = request.args.get("proveedor")
    if proveedor:
        filtros["proveedor"] = proveedor
    pagos = get_pagos(filtros)
    return render_template(
        "pagos.html",
        pagos=pagos,
        date=date,
        timedelta=timedelta
    )

@login_required
@bp_pagos.route("/pagos/update", methods=["POST"])
@require_modulo('pagos')
def update_pagos():
    supabase = current_app.config["SUPABASE"]
    nums = request.form.getlist("orden_numero[]")
    fechas = request.form.getlist("fecha_pago[]")
    any_error = False

    for i, num in enumerate(nums):
        fpago = fechas[i]
        if not fpago:
            continue
        try:
            d = datetime.strptime(fpago, "%Y-%m-%d").date()
        except ValueError:
            flash(f"Fecha inválida para OP {num}", "danger")
            any_error = True
            continue
        if d > date.today() + timedelta(days=7):
            flash(f"Fecha de pago muy futura para OP {num}", "danger")
            any_error = True
            continue
        existing = (
            supabase
            .table("fechas_de_pagos_op")
            .select("orden_numero")
            .eq("orden_numero", int(num))
            .limit(1)
            .execute()
            .data or []
        )
        if existing:
            supabase.table("fechas_de_pagos_op") \
                .update({"fecha_pago": fpago}) \
                .eq("orden_numero", int(num)) \
                .execute()
        else:
            supabase.table("fechas_de_pagos_op") \
                .insert({"orden_numero": int(num), "fecha_pago": fpago}) \
                .execute()

    if not any_error:
        flash("Fechas de pago actualizadas con éxito", "success")
    return redirect(url_for("pagos.list_pagos"))

@login_required
@bp_pagos.route('/pagos/export', methods=['GET'])
@require_modulo('pagos')
def export_pagos():
    # Toma los mismos filtros de la vista, si tienes más, agrégalos aquí
    filtros = {}
    proveedor = request.args.get("proveedor")
    if proveedor:
        filtros["proveedor"] = proveedor
    pagos = get_pagos(filtros)

    # Columnas del Excel: mismas que en pantalla (puedes ajustar orden/nombres)
    headers = [
        "fecha", "orden_numero", "proveedor_nombre", "detalle_compra",
        "factura", "total_pago", "fecha_pago", "proyecto", "orden_compra",
        "condicion_pago", "cuenta", "vencimiento", "fecha_factura"
    ]

    col_names = [
        "FECHA OP", "O.PAGO", "PROVEEDOR", "DETALLE O.PAGO",
        "FACTURA ASOCIADA", "TOTAL PAGO", "FECHA DE PAGO", "PROYECTO",
        "O. DE COMPRA", "CONDICIÓN DE PAGO", "CTA CTE PROVEEDOR",
        "VENCIMIENTO FAC.", "FECHA DE FAC."
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "Pagos"

    # Escribir cabeceras bonitas
    ws.append(col_names)
    for row in pagos:
        ws.append([row.get(h, "") for h in headers])

    # Agregar total al final (columna TOTAL PAGO)
    ws.append([])
    ws.append(["", "", "", "TOTAL GENERAL", "", sum(row["total_pago"] for row in pagos)])

    # Guardar y descargar
    output_bytes = io.BytesIO()
    wb.save(output_bytes)
    output_bytes.seek(0)
    filename = f"pagos_{date.today().isoformat()}.xlsx"
    return send_file(
        output_bytes,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )