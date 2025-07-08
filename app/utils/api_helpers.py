# app/utils/api_helpers.py

from functools import wraps
from flask import request, jsonify, current_app
from .cache import get_select2_cached_results, cache_select2_results

def optimized_select2_api(table_name, columns="id,nombre", search_column="nombre", cache_ttl=300):
    """
    Decorador para crear APIs de Select2 optimizadas con cache
    
    Args:
        table_name (str): Nombre de la tabla en Supabase
        columns (str): Columnas a seleccionar (formato Supabase)
        search_column (str): Columna donde buscar
        cache_ttl (int): TTL del cache en segundos
    
    Returns:
        function: Función decorada
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            supabase = current_app.config['SUPABASE']
            term = request.args.get("term", "").strip()
            
            # Validación mínima
            if not term or len(term) < 1:
                return jsonify({"results": []})
            
            # Intentar obtener del cache
            cached_results = get_select2_cached_results(table_name, term)
            if cached_results is not None:
                return jsonify({"results": cached_results})
            
            try:
                # Consulta optimizada con índices
                data = supabase.table(table_name) \
                    .select(columns) \
                    .ilike(search_column, f"%{term}%") \
                    .limit(20) \
                    .execute().data or []
                
                # Formatear resultados para Select2
                # Función original puede personalizar el formato
                results = func(data, *args, **kwargs)
                
                # Cachear resultados
                if results:
                    cache_select2_results(table_name, term, results)
                
                return jsonify({"results": results})
                
            except Exception as e:
                current_app.logger.error(f"Error en API {table_name}: {e}")
                return jsonify({"results": [], "error": "Error interno"}), 500
        
        return wrapper
    return decorator

def format_select2_basic(data):
    """Formateador básico para Select2: id, text"""
    return [{"id": item["id"], "text": item.get("nombre", "")} for item in data]

def format_select2_with_extra(data, extra_field):
    """Formateador para Select2 con campo extra"""
    return [{
        "id": item["id"], 
        "text": item.get("nombre", ""),
        extra_field: item.get(extra_field, "")
    } for item in data]

def optimized_search_api(table_name, search_fields, result_fields=None, cache_ttl=300):
    """
    Decorador para APIs de búsqueda más complejas
    
    Args:
        table_name (str): Nombre de la tabla
        search_fields (list): Lista de campos donde buscar
        result_fields (list): Campos a retornar (None = todos)
        cache_ttl (int): TTL del cache
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            supabase = current_app.config['SUPABASE']
            term = request.args.get("term", "").strip()
            
            if not term or len(term) < 2:
                return jsonify({"results": []})
            
            # Cache key más específico para búsquedas complejas
            cache_key = f"search_{table_name}_{'_'.join(search_fields)}_{term.lower()}"
            
            try:
                # Construir consulta OR dinámica
                or_conditions = [f"{field}.ilike.%{term}%" for field in search_fields]
                or_query = ",".join(or_conditions)
                
                select_fields = ",".join(result_fields) if result_fields else "*"
                
                data = supabase.table(table_name) \
                    .select(select_fields) \
                    .or_(or_query) \
                    .limit(15) \
                    .execute().data or []
                
                # La función original procesa los resultados
                results = func(data, *args, **kwargs)
                
                return jsonify({"results": results})
                
            except Exception as e:
                current_app.logger.error(f"Error en búsqueda {table_name}: {e}")
                return jsonify({"results": [], "error": "Error interno"}), 500
        
        return wrapper
    return decorator
