import os
import jwt
from functools import wraps
from flask import request, jsonify, current_app

def decode_auth_token(auth_token):
    """
    Decodifica el token aceptando tanto SSO (Llave Nueva) como Local (Llave Vieja).
    """
    # 1. Obtenemos ambas llaves del entorno
    sso_secret = os.getenv('JWT_SECRET_KEY') # La llave del Portal
    local_secret = os.getenv('SECRET_KEY')   # La llave antigua del proyecto

    payload = None

    # INTENTO 1: Probar con llave SSO (Prioridad)
    if sso_secret:
        try:
            # verify_signature=True es el default
            # Intentamos abrirlo como si fuera del Portal
            payload = jwt.decode(auth_token, sso_secret, algorithms=["HS256"])
            return payload # ¡Éxito!
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            pass # Falló SSO, intentamos local

    # INTENTO 2: Probar con llave Local (Para usuarios antiguos o scripts)
    if local_secret:
        try:
            payload = jwt.decode(auth_token, local_secret, algorithms=["HS256"])
            return payload
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            pass

    return "Token inválido o expirado"

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # 1. Buscar el token en el Header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        # 2. Si no hay token, rechazar
        if not token:
            return jsonify({'message': 'Token no encontrado'}), 401

        # 3. Validar usando la lógica híbrida
        resp = decode_auth_token(token)
        
        # Si resp es string, es un mensaje de error
        if isinstance(resp, str):
            current_app.logger.warning(f"🚫 Acceso denegado: {resp}")
            return jsonify({'message': resp}), 401
            
        # 4. Inyectar el usuario actual en la función
        # (Esto es lo que espera tu función 'create_orden(current_user)')
        current_user = resp 
        
        return f(current_user, *args, **kwargs)

    return decorated