# app/utils/informe_op_cache.py

"""
Sistema de cache inteligente para el módulo Informe de Órdenes de Pago
Con invalidación automática en operaciones CRUD y refresh temporal cada 5 minutos
"""

from datetime import datetime, timedelta
import hashlib
import json
import logging
from flask import current_app
from .cache import get_cached_data, set_cached_data, clear_cache

logger = logging.getLogger(__name__)

# TTL específicos para diferentes tipos de datos
CACHE_TTL = {
    'informe_data': 300,        # 5 minutos para datos principales
    'saldos_proyectos': 300,    # 5 minutos para saldos por proyecto  
    'totales': 300,             # 5 minutos para totales
    'static_data': 900          # 15 minutos para datos estáticos (proyectos, proveedores)
}

# Prefijos para keys de cache
CACHE_PREFIXES = {
    'informe': 'informe_op_data',
    'saldos': 'informe_op_saldos', 
    'totales': 'informe_op_totales',
    'static': 'informe_op_static'
}

class InformeOpCache:
    """Cache manager específico para Informe de Órdenes de Pago"""
    
    def __init__(self):
        self.last_invalidation = datetime.now()
    
    def _generate_cache_key(self, prefix, filtros=None, page=1, per_page=500):
        """Genera una clave única basada en filtros y paginación"""
        key_data = {
            'filtros': filtros or {},
            'page': page,
            'per_page': per_page
        }
        # Crear hash del contenido para key única
        content_hash = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()[:8]
        return f"{CACHE_PREFIXES[prefix]}_{content_hash}"
    
    def get_informe_data(self, filtros=None, page=1, per_page=500):
        """Obtiene datos del informe desde cache"""
        cache_key = self._generate_cache_key('informe', filtros, page, per_page)
        cached_data = get_cached_data(cache_key, ttl=CACHE_TTL['informe_data'])
        
        if cached_data:
            logger.info(f"[CACHE HIT] Informe data: {cache_key}")
            return cached_data
        
        logger.info(f"[CACHE MISS] Informe data: {cache_key}")
        return None
    
    def set_informe_data(self, data, filtros=None, page=1, per_page=500):
        """Guarda datos del informe en cache"""
        cache_key = self._generate_cache_key('informe', filtros, page, per_page)
        set_cached_data(cache_key, data, ttl=CACHE_TTL['informe_data'])
        logger.info(f"[CACHE SET] Informe data: {cache_key}")
    
    def get_saldos_proyectos(self, filtros=None):
        """Obtiene saldos por proyecto desde cache"""
        cache_key = self._generate_cache_key('saldos', filtros)
        cached_data = get_cached_data(cache_key, ttl=CACHE_TTL['saldos_proyectos'])
        
        if cached_data:
            logger.info(f"[CACHE HIT] Saldos proyectos: {cache_key}")
            return cached_data
        
        logger.info(f"[CACHE MISS] Saldos proyectos: {cache_key}")
        return None
    
    def set_saldos_proyectos(self, data, filtros=None):
        """Guarda saldos por proyecto en cache"""
        cache_key = self._generate_cache_key('saldos', filtros)
        set_cached_data(cache_key, data, ttl=CACHE_TTL['saldos_proyectos'])
        logger.info(f"[CACHE SET] Saldos proyectos: {cache_key}")
    
    def get_totales(self, filtros=None):
        """Obtiene totales desde cache"""
        cache_key = self._generate_cache_key('totales', filtros)
        cached_data = get_cached_data(cache_key, ttl=CACHE_TTL['totales'])
        
        if cached_data:
            logger.info(f"[CACHE HIT] Totales: {cache_key}")
            return cached_data
        
        logger.info(f"[CACHE MISS] Totales: {cache_key}")
        return None
    
    def set_totales(self, data, filtros=None):
        """Guarda totales en cache"""
        cache_key = self._generate_cache_key('totales', filtros)
        set_cached_data(cache_key, data, ttl=CACHE_TTL['totales'])
        logger.info(f"[CACHE SET] Totales: {cache_key}")
    
    def invalidate_all(self, reason="manual"):
        """Invalida todo el cache del módulo informe_op"""
        patterns = [
            f"{CACHE_PREFIXES['informe']}_*",
            f"{CACHE_PREFIXES['saldos']}_*", 
            f"{CACHE_PREFIXES['totales']}_*"
        ]
        
        for pattern in patterns:
            clear_cache(pattern)
        
        self.last_invalidation = datetime.now()
        logger.info(f"[CACHE INVALIDATED] Motivo: {reason}, Tiempo: {self.last_invalidation}")
    
    def invalidate_on_crud_operation(self, operation, table, orden_numero=None):
        """
        Invalida cache específico después de operaciones CRUD
        
        Args:
            operation (str): 'insert', 'update', 'delete'
            table (str): Tabla afectada  
            orden_numero (int): Número de orden afectada (opcional)
        """
        reason = f"{operation.upper()} en tabla {table}"
        if orden_numero:
            reason += f" (orden: {orden_numero})"
        
        # Invalidar todo porque los cambios afectan cálculos globales
        self.invalidate_all(reason)
        
        # Log específico para auditoría
        logger.warning(f"[CRUD INVALIDATION] {reason}")
    
    def should_refresh_static_data(self):
        """Verifica si los datos estáticos necesitan refresh"""
        return (datetime.now() - self.last_invalidation).total_seconds() > CACHE_TTL['static_data']
    
    def is_cache_fresh(self):
        """Verifica si el cache general está fresco (menos de 5 minutos)"""
        return (datetime.now() - self.last_invalidation).total_seconds() < CACHE_TTL['informe_data']

# Instancia global del cache manager para informe_op
informe_cache = InformeOpCache()

# Decorador para invalidar cache automáticamente
def invalidate_informe_cache(operation, table):
    """
    Decorador para invalidar cache automáticamente después de operaciones CRUD
    
    Uso:
    @invalidate_informe_cache('update', 'fechas_de_pagos_op')
    def update_pagos():
        # lógica de update
        pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # Ejecutar función original
                result = func(*args, **kwargs)
                
                # Invalidar cache después de éxito
                orden_numero = kwargs.get('orden_numero') or (args[0] if args else None)
                informe_cache.invalidate_on_crud_operation(operation, table, orden_numero)
                
                return result
            except Exception as e:
                # No invalidar si hay error
                logger.error(f"Error en {func.__name__}: {e}")
                raise
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator

# Función helper para debug
def get_cache_stats():
    """Retorna estadísticas del cache para debugging"""
    return {
        'last_invalidation': informe_cache.last_invalidation.isoformat(),
        'cache_age_seconds': (datetime.now() - informe_cache.last_invalidation).total_seconds(),
        'is_fresh': informe_cache.is_cache_fresh(),
        'ttl_config': CACHE_TTL
    }
