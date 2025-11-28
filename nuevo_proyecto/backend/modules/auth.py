import jwt
import datetime
from flask import Blueprint, request, jsonify, current_app
from ..models.user import User

bp = Blueprint("auth", __name__)

@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    
    # Validar que se recibió JSON
    if not data:
        return jsonify({"message": "No se recibieron datos"}), 400
    
    # Aceptar tanto 'email' como 'correo'
    email = data.get('email') or data.get('correo')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"message": "Faltan credenciales (email/correo y password requeridos)"}), 400
    
    supabase = current_app.config['SUPABASE']

    try:
        # 1. Buscar al usuario por su correo en Supabase
        user_row = supabase.table('usuarios').select('*').eq('email', email).single().execute().data
        
        if not user_row:
            return jsonify({"message": "Usuario no encontrado"}), 401

        # 2. Crear una instancia del usuario y verificar la contraseña
        user = User.from_db_row(user_row)
        if not user.check_password(password):
            return jsonify({"message": "Contraseña incorrecta"}), 401

        # 3. Si todo es correcto, generar el token JWT
        token = jwt.encode({
            'user_id': user.id,
            'nombre': user.nombre,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24) # El token expira en 24 horas
        }, current_app.config['SECRET_KEY'], algorithm="HS256")

        # Detectar si el usuario tiene contraseña temporal marcada en la BD
        temp_flag = False
        try:
            temp_flag = True if user_row.get('motivo_bloqueo') == 'CONTRASEÑA_TEMPORAL' else False
        except Exception:
            temp_flag = False

        return jsonify({
            "success": True,
            "token": token,
            "temp_password": temp_flag,
            "user": {
                "id": user.id,
                "nombre": user.nombre,
                "correo": user.correo,
                "modulos": user.modulos
            }
        })

    except Exception as e:
        return jsonify({"message": "Error en el servidor", "error": str(e)}), 500
