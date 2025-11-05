# backend/utils/cache.py
import redis
import json
import os
from functools import wraps
from flask import current_app

# Conexión a Redis (opcional - si no está disponible, el caché no se usará)
REDIS_URL = os.environ.get('REDIS_URL')
redis_client = None

if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL)
        redis_client.ping()  # Verificar conexión
        print("✓ Redis conectado exitosamente")
    except Exception as e:
        print(f"⚠ Redis no disponible: {e}")
        redis_client = None
else:
    print("⚠ REDIS_URL no configurado - caché deshabilitado")

def cache_result(ttl_seconds=300):
    """
    Decorador para cachear el resultado de una función en Redis.
    Si Redis no está disponible, simplemente ejecuta la función sin caché.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Si Redis no está disponible, ejecutar la función directamente
            if redis_client is None:
                return func(*args, **kwargs)
            
            # Crear una clave de caché única basada en el nombre de la función y sus argumentos
            cache_key = f"{func.__name__}:{json.dumps(args)}:{json.dumps(kwargs, sort_keys=True)}"
            
            try:
                # 1. Intentar obtener el resultado de la caché
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            except redis.exceptions.ConnectionError:
                # Si Redis no está disponible, simplemente ejecuta la función
                return func(*args, **kwargs)

            # 2. Si no está en caché, ejecutar la función original
            result = func(*args, **kwargs)
            
            # 3. Guardar el resultado en caché con un tiempo de expiración (TTL)
            try:
                redis_client.setex(cache_key, ttl_seconds, json.dumps(result))
            except redis.exceptions.ConnectionError:
                # No hacer nada si Redis falla al guardar
                pass
                
            return result
        return wrapper
    return decorator

def clear_cache(prefix: str):
    """
    Limpia todas las claves de caché que comiencen con un prefijo.
    Ej: clear_cache('get_proyectos')
    """
    if redis_client is None:
        return  # No hacer nada si Redis no está disponible
    
    try:
        for key in redis_client.scan_iter(f"{prefix}:*"):
            redis_client.delete(key)
    except redis.exceptions.ConnectionError:
        pass
