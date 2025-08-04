# app/utils/compression.py

import gzip
import io
from flask import request, current_app

def should_compress_response(response):
    """Determina si una respuesta debe ser comprimida"""
    # No comprimir si ya está comprimida
    if response.headers.get('Content-Encoding'):
        return False
    
    # Solo comprimir ciertos tipos de contenido
    content_type = response.content_type or ''
    compressible_types = [
        'text/html',
        'text/css',
        'text/javascript',
        'application/javascript',
        'application/json',
        'text/xml',
        'application/xml'
    ]
    
    for comp_type in compressible_types:
        if comp_type in content_type:
            return True
    
    return False

def compress_response(response):
    """Comprime una respuesta usando gzip"""
    # No comprimir si la respuesta está en modo direct_passthrough (ej. send_file)
    if getattr(response, 'direct_passthrough', False):
        return response
    if not should_compress_response(response):
        return response
    # Solo comprimir respuestas grandes (>1KB)
    if len(response.data) < 1024:
        return response
    
    # Verificar que el cliente acepta gzip
    accept_encoding = request.headers.get('Accept-Encoding', '')
    if 'gzip' not in accept_encoding:
        return response
    
    try:
        # Comprimir el contenido
        compressed_data = gzip.compress(response.data)
        
        # Solo usar si realmente reduce el tamaño
        if len(compressed_data) < len(response.data):
            response.data = compressed_data
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Content-Length'] = len(compressed_data)
            response.headers['Vary'] = 'Accept-Encoding'
    except Exception as e:
        current_app.logger.warning(f"Error comprimiendo respuesta: {e}")
    
    return response

def setup_compression(app):
    """Configura compresión automática para la app"""
    
    @app.after_request
    def compress_responses(response):
        return compress_response(response)
