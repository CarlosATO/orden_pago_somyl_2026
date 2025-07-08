# app/utils/static_data.py

"""
Sistema de cache para datos estáticos que se cargan frecuentemente
como proyectos, items, trabajadores, etc.
"""

from flask import current_app
from .cache import get_cached_data, set_cached_data

# TTL más largo para datos que cambian poco
STATIC_DATA_TTL = 900  # 15 minutos

def get_cached_proyectos():
    """Obtiene lista de proyectos con cache de 15 minutos"""
    cached = get_cached_data("static_proyectos", ttl=STATIC_DATA_TTL)
    if cached is not None:
        return cached
    
    supabase = current_app.config["SUPABASE"]
    try:
        data = supabase.table("proyectos").select("id,proyecto").limit(200).execute().data or []
        proyectos = [p['proyecto'] for p in data]
        set_cached_data("static_proyectos", proyectos)
        return proyectos
    except Exception as e:
        current_app.logger.error(f"Error cargando proyectos: {e}")
        return []

def get_cached_items():
    """Obtiene lista de items con cache de 15 minutos"""
    cached = get_cached_data("static_items", ttl=STATIC_DATA_TTL)
    if cached is not None:
        return cached
    
    supabase = current_app.config["SUPABASE"]
    try:
        data = supabase.table("item").select("id,tipo").limit(200).execute().data or []
        items = [i['tipo'] for i in data]
        set_cached_data("static_items", items)
        return items
    except Exception as e:
        current_app.logger.error(f"Error cargando items: {e}")
        return []

def get_cached_trabajadores():
    """Obtiene lista de trabajadores con cache de 15 minutos"""
    cached = get_cached_data("static_trabajadores", ttl=STATIC_DATA_TTL)
    if cached is not None:
        return cached
    
    supabase = current_app.config["SUPABASE"]
    try:
        data = supabase.table("trabajadores").select("id,nombre").limit(500).execute().data or []
        trabajadores = [t['nombre'] for t in data]
        set_cached_data("static_trabajadores", trabajadores)
        return trabajadores
    except Exception as e:
        current_app.logger.error(f"Error cargando trabajadores: {e}")
        return []

def get_cached_proveedores():
    """Obtiene lista de proveedores con cache de 15 minutos"""
    cached = get_cached_data("static_proveedores", ttl=STATIC_DATA_TTL)
    if cached is not None:
        return cached
    
    supabase = current_app.config["SUPABASE"]
    try:
        data = supabase.table("proveedores").select("id,nombre,cuenta").limit(500).execute().data or []
        set_cached_data("static_proveedores", data)
        return data
    except Exception as e:
        current_app.logger.error(f"Error cargando proveedores: {e}")
        return []

def get_cached_proyectos_with_id():
    """Obtiene proyectos con ID para selects que necesitan value/text"""
    cached = get_cached_data("static_proyectos_id", ttl=STATIC_DATA_TTL)
    if cached is not None:
        return cached
    
    supabase = current_app.config["SUPABASE"]
    try:
        data = supabase.table("proyectos").select("id,proyecto").limit(200).execute().data or []
        set_cached_data("static_proyectos_id", data)
        return data
    except Exception as e:
        current_app.logger.error(f"Error cargando proyectos con ID: {e}")
        return []

def get_cached_items_with_id():
    """Obtiene items con ID para selects que necesitan value/text"""
    cached = get_cached_data("static_items_id", ttl=STATIC_DATA_TTL)
    if cached is not None:
        return cached
    
    supabase = current_app.config["SUPABASE"]
    try:
        data = supabase.table("item").select("id,tipo").limit(200).execute().data or []
        set_cached_data("static_items_id", data)
        return data
    except Exception as e:
        current_app.logger.error(f"Error cargando items con ID: {e}")
        return []

def clear_static_cache():
    """Limpia todo el cache de datos estáticos"""
    from .cache import clear_cache
    clear_cache("static_")

# Función helper para invalidar cache cuando se crean/editan registros
def invalidate_static_cache(table_name):
    """Invalida cache específico cuando se modifica una tabla"""
    from .cache import clear_cache
    cache_map = {
        'proyectos': ['static_proyectos', 'static_proyectos_id'],
        'item': ['static_items', 'static_items_id'],
        'trabajadores': ['static_trabajadores'],
        'proveedores': ['static_proveedores']
    }
    
    if table_name in cache_map:
        for cache_key in cache_map[table_name]:
            clear_cache(cache_key)
