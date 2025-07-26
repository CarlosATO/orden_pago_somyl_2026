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
import json
from app.utils.static_data import get_cached_proveedores, get_cached_proyectos_with_id

bp_pagos = Blueprint(
    "pagos", __name__,
    template_folder="../templates"
)

def get_pagos(filtros=None):
    supabase = current_app.config["SUPABASE"]
    # Trae y agrupa igual que la vista
    # Traer todos los registros usando paginación manual
    page_size = 1000
    offset = 0
    all_rows = []
    while True:
        batch = supabase \
            .table("orden_de_pago") \
            .select(
                "orden_numero, fecha, proveedor_nombre, detalle_compra, factura, "
                "costo_final_con_iva, proyecto, orden_compra, condicion_pago, vencimiento, fecha_factura"
            ) \
            .order("orden_numero") \
            .range(offset, offset + page_size - 1) \
            .execute() \
            .data or []
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    # Print temporal para diagnóstico
    print("[DEBUG] Total registros traídos:", len(all_rows))




    # Aplicar filtros si corresponde (aquí puedes adaptar según tus filtros)
    if filtros:
        if filtros.get("proveedor"):
            all_rows = [r for r in all_rows if r["proveedor_nombre"] == filtros["proveedor"]]

    # Agrupar por orden_numero único, sumar montos, y tomar los demás datos del primer registro
    pagos = {}
    ordenes_unicos_tabla = set()
    ordenes_informe = set()
    ordenes_no_convertibles = set()
    for r in all_rows:
        ordenes_unicos_tabla.add(r["orden_numero"])
        try:
            num = int(r["orden_numero"])
        except Exception:
            ordenes_no_convertibles.add(r["orden_numero"])
            continue  # Si no se puede convertir, omitir
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
        ordenes_informe.add(num)

    # ...logs temporales eliminados...
    # Ordenar de mayor a menor por orden_numero
    pagos_ordenados = [pagos[k] for k in sorted(pagos.keys(), reverse=True)]

    # Fechas de pago existentes
    pagos_guardados = (
        supabase
        .table("fechas_de_pagos_op")
        .select("orden_numero, fecha_pago")
        .execute()
        .data or []
    )
    fecha_map = {p["orden_numero"]: p["fecha_pago"] for p in pagos_guardados}
    for data in pagos_ordenados:
        data["fecha_pago"] = fecha_map.get(data["orden_numero"])

    # Cuentas corrientes de proveedores - usar datos cacheados
    provs = get_cached_proveedores()
    cuenta_map = {p["nombre"]: p["cuenta"] for p in provs}
    for data in pagos_ordenados:
        data["cuenta"] = cuenta_map.get(data["proveedor_nombre"], "")

    # Nombres de proyectos - usar datos cacheados
    projs = get_cached_proyectos_with_id()
    proyecto_map = {pr["id"]: pr["proyecto"] for pr in projs}
    for data in pagos_ordenados:
        proj_id = data.get("proyecto")
        data["proyecto"] = proyecto_map.get(proj_id, proj_id)

    # Retorna la lista ordenada
    return pagos_ordenados

@login_required
@bp_pagos.route("/pagos", methods=["GET"])
@require_modulo('pagos')
def list_pagos():
    # Recoger filtros de la URL
    filtros = {}
    proveedor = request.args.get("proveedor", "").strip()
    proyecto = request.args.get("proyecto", "").strip()
    estado = request.args.get("estado", "").strip()  # pagado, pendiente, vencido
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    
    if proveedor:
        filtros["proveedor"] = proveedor
    if proyecto:
        filtros["proyecto"] = proyecto
    if estado:
        filtros["estado"] = estado
    if fecha_desde:
        filtros["fecha_desde"] = fecha_desde
    if fecha_hasta:
        filtros["fecha_hasta"] = fecha_hasta
    
    pagos = get_pagos(filtros)

    # Calcular el total pendiente igual que en la plantilla
    total_pendiente = sum(p["total_pago"] for p in pagos if not p["fecha_pago"])

    # Datos adicionales para el template
    proveedores_unicos = sorted(set(p["proveedor_nombre"] for p in pagos))
    proyectos_unicos = sorted(set(p["proyecto"] for p in pagos))

    # Calcular fecha máxima para el input de fecha (hoy + 7 días)
    fecha_maxima = (date.today() + timedelta(days=7)).isoformat()

    return render_template(
        "pagos.html",
        pagos=pagos,
        fecha_maxima=fecha_maxima,
        proveedores_unicos=proveedores_unicos,
        proyectos_unicos=proyectos_unicos,
        filtros_activos=filtros,
        total_pendiente=total_pendiente
    )

@login_required
@bp_pagos.route("/pagos/update", methods=["POST"])
@require_modulo('pagos')
def update_pagos():
    supabase = current_app.config["SUPABASE"]
    nums = request.form.getlist("orden_numero[]")
    fechas = request.form.getlist("fecha_pago[]")
    any_error = False
    upserts = []
    deletes = []

    for i, num in enumerate(nums):
        fpago = fechas[i].strip() if i < len(fechas) else ""
        if fpago:
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
            upserts.append({"orden_numero": int(num), "fecha_pago": fpago})
        else:
            # Si el campo está vacío, eliminar la fila completa
            deletes.append(int(num))

    # Upsert masivo si hay datos válidos
    if upserts:
        supabase.table("fechas_de_pagos_op").upsert(upserts, on_conflict=["orden_numero"]).execute()

    # Eliminar filas completas para las fechas borradas en una sola consulta
    if deletes:
        supabase.table("fechas_de_pagos_op").delete().in_("orden_numero", deletes).execute()

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
    # Log temporal eliminado