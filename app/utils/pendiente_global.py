from flask import current_app

def get_total_pendiente_global():
    supabase = current_app.config["SUPABASE"]
    # Traer todas las órdenes de pago usando paginación manual
    page_size = 1000
    offset = 0
    todas_op = []
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
        todas_op.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    # Traer todas las fechas de pago (pagadas)
    pagadas = (
        supabase
        .table("fechas_de_pagos_op")
        .select("orden_numero")
        .execute()
        .data or []
    )
    # Crear set de ordenes pagadas
    pagadas_set = set(p["orden_numero"] for p in pagadas)
    # Sumar solo las órdenes que NO están en pagadas_set
    total = sum(float(op.get("costo_final_con_iva", 0) or 0)
                for op in todas_op if op["orden_numero"] not in pagadas_set)
    return total
