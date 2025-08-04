# Función para invalidar el cache de Select2 por tabla
def invalidate_select2_cache(table):
    pattern = f"select2_{table}_"
    clear_cache(pattern)
# app/utils/cache.py

from datetime import datetime, timedelta
import logging

# Cache global para todos los módulos
_global_cache = {
    'data': {},
    'timestamps': {},
    'ttl_default': 300  # 5 minutos por defecto
}

def get_cached_data(key, ttl=None):
    """
    Obtiene datos del cache global si están vigentes
    
    Args:
        key (str): Clave del cache
        ttl (int): TTL en segundos, usa default si no se especifica
    
    Returns:
        list/dict/None: Datos cached o None si no están vigentes
    """
    if ttl is None:
        ttl = _global_cache['ttl_default']
    
    now = datetime.now()
    timestamp = _global_cache['timestamps'].get(key)
    
    if (timestamp and 
        now - timestamp < timedelta(seconds=ttl)):
        return _global_cache['data'].get(key)
    
    return None

def set_cached_data(key, data, ttl=None):
    """
    Guarda datos en el cache global
    
    Args:
        key (str): Clave del cache
        data: Datos a cachear
        ttl (int): TTL en segundos (opcional)
    """
    _global_cache['timestamps'][key] = datetime.now()
    _global_cache['data'][key] = data

def clear_cache(pattern=None):
    """
    Limpia el cache. Si se especifica pattern, solo limpia claves que lo contengan
    
    Args:
        pattern (str): Patrón para filtrar claves a limpiar
    """
    if pattern:
        keys_to_remove = [k for k in _global_cache['data'].keys() if pattern in k]
        for key in keys_to_remove:
            _global_cache['data'].pop(key, None)
            _global_cache['timestamps'].pop(key, None)
    else:
        _global_cache['data'].clear()
        _global_cache['timestamps'].clear()

def search_cached_data(key, term):
    """
    Busca en datos cacheados usando un término de búsqueda
    
    Args:
        key (str): Clave del cache
        term (str): Término de búsqueda
    
    Returns:
        list: Resultados filtrados o lista vacía
    """
    cached_data = get_cached_data(key)
    if cached_data is None:
        return None
    
    # Si el cache contiene resultados de búsquedas, filtrar por término
    filtered_results = []
    term_lower = term.lower()
    
    for item in cached_data:
        # Buscar en el campo 'text' que es estándar en Select2
        if 'text' in item and term_lower in item['text'].lower():
            filtered_results.append(item)
    
    return filtered_results[:20]  # Limitar resultados

# Funciones específicas para optimización común
def get_select2_cache_key(table, term):
    """Genera clave de cache estándar para Select2"""
    return f"select2_{table}_{term.lower()}"

def cache_select2_results(table, term, results):
    """Cachea resultados de Select2 de forma estándar"""
    cache_key = get_select2_cache_key(table, term)
    set_cached_data(cache_key, results)

def get_select2_cached_results(table, term):
    """Obtiene resultados cacheados de Select2"""
    cache_key = get_select2_cache_key(table, term)
    return get_cached_data(cache_key)

# Configuración de logging para debug
logger = logging.getLogger(__name__)

# Exportar objeto cache para compatibilidad
class CacheManager:
    """Clase para gestionar el cache global"""
    
    def get(self, key, ttl=None):
        return get_cached_data(key, ttl)
    
    def set(self, key, data, ttl=None):
        return set_cached_data(key, data, ttl)
    
    def clear(self, pattern=None):
        return clear_cache(pattern)
    
    def search(self, key, term):
        return search_cached_data(key, term)

# Instancia global del cache
cache = CacheManager()
