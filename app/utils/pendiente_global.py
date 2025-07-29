from flask import current_app

def get_total_pendiente_global():

    supabase = current_app.config["SUPABASE"]
    # 1. Traer todas las órdenes de pago y agrupar por orden_numero, sumando costo_final_con_iva
    page_size = 1000
    offset = 0
    all_rows = []
    while True:
        batch = (
            supabase
            .table("orden_de_pago")
            .select("orden_numero, costo_final_con_iva")
            .order("orden_numero")
            .range(offset, offset + page_size - 1)
            .execute()
            .data or []
        )
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    pagos = {}
    for r in all_rows:
        try:
            num = int(r["orden_numero"])
        except Exception:
            continue
        if num not in pagos:
            pagos[num] = {
                "orden_numero": num,
                "total_pago": 0.0,
                "fecha_pago": None
            }
        pagos[num]["total_pago"] += float(r.get("costo_final_con_iva") or 0)

    # 2. Traer todas las fechas de pago (pagadas)
    page_size = 1000
    offset = 0
    pagos_guardados = []
    while True:
        batch = (
            supabase
            .table("fechas_de_pagos_op")
            .select("orden_numero, fecha_pago")
            .order("orden_numero")
            .range(offset, offset + page_size - 1)
            .execute()
            .data or []
        )
        pagos_guardados.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    fecha_map = {str(row.get("orden_numero")): row.get("fecha_pago") for row in pagos_guardados}
    for data in pagos.values():
        data["fecha_pago"] = fecha_map.get(str(data["orden_numero"]))

    # 3. Sumar solo los total_pago de las órdenes que no tienen fecha_pago
    total_pendiente = sum(p["total_pago"] for p in pagos.values() if not p["fecha_pago"])
    return total_pendiente
