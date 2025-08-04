from flask import current_app
from app.utils.performance_monitor import time_function

@time_function("get_total_pendiente_global")
def get_total_pendiente_global():
    """Versión optimizada con batch processing y cache"""
    from app.utils.cache import get_cached_data, set_cached_data
    
    # Cache por 10 minutos
    cached_result = get_cached_data("pendiente_global_calculation", ttl=600)
    if cached_result is not None:
        return cached_result

    supabase = current_app.config["SUPABASE"]
    
    # 1. Optimización: Usar agregación SQL directa en lugar de Python
    try:
        # Consulta optimizada usando agregación en la DB
        pagos_result = (
            supabase
            .rpc('get_total_pendiente_optimized')  # Stored procedure personalizada
            .execute()
        )
        
        if pagos_result.data and len(pagos_result.data) > 0:
            total_pendiente = float(pagos_result.data[0].get('total_pendiente', 0))
            set_cached_data("pendiente_global_calculation", total_pendiente)
            return total_pendiente
    except Exception:
        # Fallback al método original pero optimizado
        pass
    
    # 2. Fallback optimizado: Batch processing más eficiente
    page_size = 2000  # Páginas más grandes
    
    # Optimización: Usar query más específico para solo lo necesario
    all_rows = []
    offset = 0
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

    # Procesamiento optimizado en memoria
    pagos = {}
    for r in all_rows:
        try:
            num = int(r["orden_numero"])
            costo = float(r.get("costo_final_con_iva") or 0)
        except (ValueError, TypeError):
            continue
        
        if num not in pagos:
            pagos[num] = {"total_pago": 0.0}
        pagos[num]["total_pago"] += costo

    # 3. Consulta optimizada de fechas de pago
    offset = 0
    pagos_guardados = []
    while True:
        batch = (
            supabase
            .table("fechas_de_pagos_op")
            .select("orden_numero, fecha_pago")
            .is_("fecha_pago", "not.null")  # Solo los que tienen fecha
            .order("orden_numero")
            .range(offset, offset + page_size - 1)
            .execute()
            .data or []
        )
        pagos_guardados.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    # Crear set para lookup O(1) en lugar de dict
    fechas_pagadas = {str(row.get("orden_numero")) for row in pagos_guardados if row.get("fecha_pago")}

    # 4. Calcular total pendiente optimizado
    total_pendiente = sum(
        p["total_pago"] 
        for num, p in pagos.items() 
        if str(num) not in fechas_pagadas
    )
    
    # Cachear resultado
    set_cached_data("pendiente_global_calculation", total_pendiente)
    return total_pendiente
