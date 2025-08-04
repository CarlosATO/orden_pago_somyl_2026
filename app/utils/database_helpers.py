# app/utils/database_helpers.py

from flask import current_app
from app.utils.performance_monitor import time_function
from app.utils.cache import get_cached_data, set_cached_data
import math

@time_function("optimized_fetch_all_rows")
def optimized_fetch_all_rows(table, select_str, order_col=None, desc=False, limit=None, cache_ttl=300):
    """
    Versión optimizada de fetch_all_rows con cache y mejores prácticas
    
    Args:
        table (str): Nombre de la tabla
        select_str (str): Campos a seleccionar
        order_col (str): Columna de ordenamiento
        desc (bool): Orden descendente
        limit (int): Límite máximo de registros
        cache_ttl (int): TTL del cache en segundos
    
    Returns:
        list: Resultados de la consulta
    """
    # Cache key basado en parámetros
    cache_key = f"fetch_all_{table}_{select_str}_{order_col}_{desc}_{limit}"
    
    # Intentar obtener del cache
    cached_data = get_cached_data(cache_key, ttl=cache_ttl)
    if cached_data is not None:
        return cached_data
    
    supabase = current_app.config['SUPABASE']
    
    # Estrategia optimizada para diferentes tamaños
    if limit and limit <= 100:
        # Para consultas pequeñas, una sola query
        query = supabase.table(table).select(select_str)
        if order_col:
            query = query.order(order_col, desc=desc)
        if limit:
            query = query.limit(limit)
        
        all_rows = query.execute().data or []
    else:
        # Para consultas grandes, paginación optimizada
        page_size = min(2000, limit if limit else 2000)  # Páginas más grandes
        offset = 0
        all_rows = []
        
        while True:
            query = supabase.table(table).select(select_str)
            if order_col:
                query = query.order(order_col, desc=desc)
            query = query.range(offset, offset + page_size - 1)
            
            batch = query.execute().data or []
            all_rows.extend(batch)
            
            # Condiciones de parada optimizadas
            if (len(batch) < page_size or 
                (limit and len(all_rows) >= limit)):
                break
            
            offset += page_size
        
        # Aplicar límite si se especificó
        if limit:
            all_rows = all_rows[:limit]
    
    # Cachear resultados
    set_cached_data(cache_key, all_rows)
    return all_rows

@time_function("optimized_paginated_query")
def optimized_paginated_query(table, select_str, filters=None, order_col=None, desc=False, page=0, page_size=50):
    """
    Consulta paginada optimizada para listados grandes
    
    Args:
        table (str): Nombre de la tabla
        select_str (str): Campos a seleccionar
        filters (dict): Filtros a aplicar
        order_col (str): Columna de ordenamiento
        desc (bool): Orden descendente
        page (int): Página actual (0-indexed)
        page_size (int): Tamaño de página
    
    Returns:
        dict: {"data": [...], "total": int, "has_more": bool}
    """
    supabase = current_app.config['SUPABASE']
    
    # Construir query base
    query = supabase.table(table).select(select_str)
    
    # Aplicar filtros si se proporcionan
    if filters:
        for field, value in filters.items():
            if isinstance(value, list):
                query = query.in_(field, value)
            else:
                query = query.eq(field, value)
    
    # Aplicar ordenamiento
    if order_col:
        query = query.order(order_col, desc=desc)
    
    # Aplicar paginación
    start = page * page_size
    end = start + page_size - 1
    query = query.range(start, end)
    
    # Ejecutar consulta
    result = query.execute()
    data = result.data or []
    
    # Determinar si hay más páginas (estimación optimizada)
    has_more = len(data) == page_size
    
    # Obtener total solo si es la primera página (optimización)
    total = None
    if page == 0:
        try:
            count_query = supabase.table(table).select("id", count='exact')
            if filters:
                for field, value in filters.items():
                    if isinstance(value, list):
                        count_query = count_query.in_(field, value)
                    else:
                        count_query = count_query.eq(field, value)
            
            count_result = count_query.execute()
            total = getattr(count_result, 'count', len(data))
        except Exception:
            total = len(data)
    
    return {
        "data": data,
        "total": total,
        "has_more": has_more,
        "page": page,
        "page_size": page_size
    }

def get_table_statistics(table_name):
    """Obtiene estadísticas básicas de una tabla para optimización"""
    supabase = current_app.config['SUPABASE']
    
    try:
        # Obtener conteo total
        count_result = supabase.table(table_name).select("id", count='exact').execute()
        total_rows = getattr(count_result, 'count', 0)
        
        # Determinar estrategia óptima basada en tamaño
        if total_rows < 1000:
            strategy = "single_query"
            recommended_page_size = total_rows
        elif total_rows < 10000:
            strategy = "small_pagination"
            recommended_page_size = 500
        else:
            strategy = "large_pagination"
            recommended_page_size = 1000
        
        return {
            "total_rows": total_rows,
            "strategy": strategy,
            "recommended_page_size": recommended_page_size
        }
    except Exception as e:
        current_app.logger.error(f"Error getting table stats for {table_name}: {e}")
        return {
            "total_rows": 0,
            "strategy": "unknown",
            "recommended_page_size": 100
        }

# Funciones específicas para tablas comunes
def get_cached_proveedores(refresh=False):
    """Obtiene proveedores con cache optimizado"""
    if refresh:
        from app.utils.cache import clear_cache
        clear_cache("proveedores_")
    
    return optimized_fetch_all_rows(
        table="proveedores",
        select_str="id,nombre,rut",
        order_col="nombre",
        limit=1000,  # Límite razonable
        cache_ttl=900  # 15 minutos
    )

def get_cached_proyectos(refresh=False):
    """Obtiene proyectos con cache optimizado"""
    if refresh:
        from app.utils.cache import clear_cache
        clear_cache("proyectos_")
    
    return optimized_fetch_all_rows(
        table="proyectos",
        select_str="id,proyecto",
        order_col="proyecto",
        limit=500,
        cache_ttl=900
    )

def get_cached_trabajadores(refresh=False):
    """Obtiene trabajadores con cache optimizado"""
    if refresh:
        from app.utils.cache import clear_cache
        clear_cache("trabajadores_")
    
    return optimized_fetch_all_rows(
        table="trabajadores",
        select_str="id,nombre",
        order_col="nombre",
        limit=200,
        cache_ttl=900
    )
