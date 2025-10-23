import jwt
from functools import wraps
from flask import request, jsonify, current_app
from backend.models.user import User

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Busca el token en el encabezado 'x-access-token'
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        
        # También busca en 'Authorization: Bearer <token>'
        elif 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'message': 'Falta el token de autenticación'}), 401

        try:
            # Decodifica el token usando la SECRET_KEY de la app
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            
            # Busca al usuario en la base de datos
            supabase = current_app.config['SUPABASE']
            user_row = supabase.table('usuarios').select('*').eq('id', data['user_id']).single().execute().data
            
            if not user_row:
                 return jsonify({'message': 'Usuario del token no encontrado'}), 401
            
            current_user = User.from_db_row(user_row)

        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'El token ha expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'El token es inválido'}), 401
        except Exception as e:
            return jsonify({'message': 'Error al procesar el token', 'error': str(e)}), 500

        # Pasa el objeto 'current_user' a la ruta protegida
        return f(current_user, *args, **kwargs)

    return decorated
