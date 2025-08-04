# app/utils/performance_monitor.py

import time
import functools
import logging
from flask import current_app, request

# Configurar logger específico para performance
performance_logger = logging.getLogger('performance')

def time_function(func_name=None):
    """Decorador para medir tiempo de ejecución de funciones"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log solo si es lento (>100ms)
                if execution_time > 0.1:
                    name = func_name or f"{func.__module__}.{func.__name__}"
                    current_app.logger.warning(f"SLOW_FUNCTION: {name} took {execution_time:.3f}s")
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                name = func_name or f"{func.__module__}.{func.__name__}"
                current_app.logger.error(f"ERROR_FUNCTION: {name} failed after {execution_time:.3f}s: {e}")
                raise
        return wrapper
    return decorator

def monitor_request_performance():
    """Middleware para monitorear performance de requests"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            path = request.path
            method = request.method
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log requests lentos (>500ms)
                if execution_time > 0.5:
                    current_app.logger.warning(
                        f"SLOW_REQUEST: {method} {path} took {execution_time:.3f}s"
                    )
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                current_app.logger.error(
                    f"ERROR_REQUEST: {method} {path} failed after {execution_time:.3f}s: {e}"
                )
                raise
        return wrapper
    return decorator

class PerformanceContext:
    """Context manager para medir bloques de código"""
    def __init__(self, operation_name):
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.time() - self.start_time
        if execution_time > 0.1:  # Log si toma más de 100ms
            current_app.logger.info(f"PERFORMANCE: {self.operation_name} took {execution_time:.3f}s")
