"""
Módulo de gestión de usuarios adaptado para trabajar con frontend React
Incluye CRUD completo, gestión de permisos, bloqueo/desbloqueo y reset de contraseñas
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from backend.utils.decorators import token_required
from datetime import datetime
import secrets
import string
import re

bp = Blueprint("usuarios", __name__)


# ========= Funciones Auxiliares =========

def validar_email(email):
    """Valida el formato del email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validar_password(password):
    """Valida que la contraseña cumpla con los requisitos mínimos"""
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    return True, ""


def generar_password_temporal():
    """Genera una contraseña temporal segura de 12 caracteres"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(12))


def obtener_modulos_usuario(supabase, usuario_id):
    """Obtiene los módulos asignados a un usuario"""
    try:
        modulos_rel = supabase.table('usuario_modulo').select(
            'modulo_id, modulos(id, nombre_modulo)'
        ).eq('usuario_id', usuario_id).execute().data or []
        
        return [m['modulos']['nombre_modulo'] for m in modulos_rel if m.get('modulos')]
    except Exception as e:
        current_app.logger.error(f"Error obteniendo módulos del usuario {usuario_id}: {e}")
        return []


# ================================================================
# ENDPOINTS CRUD DE USUARIOS
# ================================================================

@bp.route("/todos", methods=["GET"])
@token_required
def api_get_usuarios(current_user):
    """
    Obtiene lista de todos los usuarios con sus módulos y estadísticas
    Query params opcionales:
    - estado: 'activos', 'inactivos', 'bloqueados', 'todos' (default)
    - buscar: término de búsqueda en nombre/email
    """
    try:
        supabase = current_app.config['SUPABASE']
        
        # Parámetros de filtro
        filtro_estado = request.args.get('estado', 'todos')
        buscar = request.args.get('buscar', '').strip()
        
        # Consulta base con paginación
        all_usuarios = []
        start = 0
        page_size = 1000
        
        while True:
            query = supabase.table('usuarios').select(
                'id, nombre, email, activo, bloqueado, fecha_creacion, fecha_ultimo_acceso, intentos_fallidos, motivo_bloqueo'
            ).range(start, start + page_size - 1).order('nombre')
            
            # Aplicar filtros
            if filtro_estado == 'activos':
                query = query.eq('activo', True)
            elif filtro_estado == 'inactivos':
                query = query.eq('activo', False)
            elif filtro_estado == 'bloqueados':
                query = query.eq('bloqueado', True)
            
            batch = query.execute().data or []
            if not batch:
                break
            
            all_usuarios.extend(batch)
            
            if len(batch) < page_size:
                break
            
            start += page_size
        
        # Filtro de búsqueda en memoria (más eficiente para este caso)
        if buscar:
            buscar_lower = buscar.lower()
            all_usuarios = [
                u for u in all_usuarios 
                if buscar_lower in u.get('nombre', '').lower() or buscar_lower in u.get('email', '').lower()
            ]
        
        # Obtener módulos de cada usuario
        for usuario in all_usuarios:
            usuario['modulos'] = obtener_modulos_usuario(supabase, usuario['id'])
        
        # Calcular estadísticas
        stats = {
            'total': len(all_usuarios),
            'activos': len([u for u in all_usuarios if u.get('activo', True)]),
            'inactivos': len([u for u in all_usuarios if not u.get('activo', True)]),
            'bloqueados': len([u for u in all_usuarios if u.get('bloqueado', False)]),
            'con_intentos_fallidos': len([u for u in all_usuarios if u.get('intentos_fallidos', 0) > 0])
        }
        
        return jsonify({
            "success": True,
            "data": all_usuarios,
            "stats": stats,
            "filtro_aplicado": filtro_estado,
            "termino_busqueda": buscar
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en api_get_usuarios: {str(e)}")
        return jsonify({"success": False, "message": f"Error al obtener usuarios: {str(e)}"}), 500


@bp.route("/<int:id>", methods=["GET"])
@token_required
def api_get_usuario_by_id(current_user, id):
    """
    Obtiene los datos de un usuario por ID, incluyendo sus módulos
    """
    try:
        supabase = current_app.config['SUPABASE']
        
        usuario = supabase.table('usuarios').select('*').eq('id', id).single().execute().data
        
        if not usuario:
            return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
        
        # Obtener módulos del usuario
        usuario['modulos'] = obtener_modulos_usuario(supabase, id)
        
        # No devolver el password
        if 'password' in usuario:
            del usuario['password']
        
        return jsonify({
            "success": True,
            "data": usuario
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en api_get_usuario_by_id: {str(e)}")
        return jsonify({"success": False, "message": f"Error al obtener usuario: {str(e)}"}), 500


@bp.route("/new", methods=["POST"])
@token_required
def new_usuario(current_user):
    """
    Crea un nuevo usuario con sus módulos asignados
    Body JSON:
    {
        "nombre": "string",
        "email": "string",
        "password": "string",
        "activo": boolean (opcional, default true),
        "modulos": [id1, id2, ...]
    }
    """
    try:
        data = request.get_json()
        
        nombre = data.get("nombre", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        activo = data.get("activo", True)
        modulos_seleccionados = data.get("modulos", [])
        
        # Validaciones
        if not nombre or not email or not password:
            return jsonify({
                "success": False,
                "message": "Nombre, email y contraseña son obligatorios"
            }), 400
        
        # Validar email
        if not validar_email(email):
            return jsonify({
                "success": False,
                "message": "El formato del correo electrónico no es válido"
            }), 400
        
        # Validar password
        password_valido, password_error = validar_password(password)
        if not password_valido:
            return jsonify({"success": False, "message": password_error}), 400
        
        # Validar módulos
        if not modulos_seleccionados or len(modulos_seleccionados) == 0:
            return jsonify({
                "success": False,
                "message": "Debe seleccionar al menos un módulo"
            }), 400
        
        supabase = current_app.config['SUPABASE']
        
        # Verificar si el email ya existe
        existe = supabase.table('usuarios').select('id').eq('email', email).execute().data
        if existe:
            return jsonify({
                "success": False,
                "message": "Ya existe un usuario con este email"
            }), 400
        
        # Crear usuario
        hashed_password = generate_password_hash(password)
        user_data = {
            'nombre': nombre,
            'email': email,
            'password': hashed_password,
            'activo': activo,
            'bloqueado': False,
            'intentos_fallidos': 0,
            'fecha_creacion': datetime.now().isoformat()
        }
        
        res = supabase.table('usuarios').insert(user_data).execute()
        
        if not res.data:
            return jsonify({
                "success": False,
                "message": "Error al crear el usuario en la base de datos"
            }), 500
        
        usuario_id = res.data[0]['id']
        
        # Insertar módulos seleccionados
        modulos_insertados = 0
        for modulo_id in modulos_seleccionados:
            try:
                supabase.table('usuario_modulo').insert({
                    'usuario_id': int(usuario_id),
                    'modulo_id': int(modulo_id)
                }).execute()
                modulos_insertados += 1
            except Exception as e:
                current_app.logger.error(f"Error insertando módulo {modulo_id} para usuario {usuario_id}: {e}")
        
        return jsonify({
            "success": True,
            "message": f"Usuario creado correctamente con {modulos_insertados} módulos asignados",
            "data": {
                "id": usuario_id,
                "nombre": nombre,
                "email": email
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en new_usuario: {str(e)}")
        return jsonify({"success": False, "message": f"Error al crear usuario: {str(e)}"}), 500


@bp.route("/edit/<int:id>", methods=["PUT"])
@token_required
def edit_usuario(current_user, id):
    """
    Actualiza los datos básicos de un usuario (nombre, email)
    Body JSON:
    {
        "nombre": "string",
        "email": "string"
    }
    """
    try:
        data = request.get_json()
        
        nombre = data.get("nombre", "").strip()
        email = data.get("email", "").strip().lower()
        
        # Validaciones
        if not nombre or not email:
            return jsonify({
                "success": False,
                "message": "Nombre y email son obligatorios"
            }), 400
        
        # Validar email
        if not validar_email(email):
            return jsonify({
                "success": False,
                "message": "El formato del correo electrónico no es válido"
            }), 400
        
        supabase = current_app.config['SUPABASE']
        
        # Verificar que el usuario existe
        usuario_actual = supabase.table('usuarios').select('id, nombre, email').eq('id', id).single().execute().data
        if not usuario_actual:
            return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
        
        # Verificar si el email ya está en uso por otro usuario
        if email != usuario_actual['email']:
            existe = supabase.table('usuarios').select('id').eq('email', email).execute().data
            if existe:
                return jsonify({
                    "success": False,
                    "message": "Ya existe otro usuario con este email"
                }), 400
        
        # Actualizar usuario
        supabase.table('usuarios').update({
            'nombre': nombre,
            'email': email
        }).eq('id', id).execute()
        
        return jsonify({
            "success": True,
            "message": "Usuario actualizado correctamente"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en edit_usuario: {str(e)}")
        return jsonify({"success": False, "message": f"Error al actualizar usuario: {str(e)}"}), 500


# ================================================================
# ENDPOINTS DE GESTIÓN DE ESTADO Y PERMISOS
# ================================================================

@bp.route("/toggle-estado/<int:id>", methods=["POST"])
@token_required
def toggle_estado_usuario(current_user, id):
    """
    Activa o desactiva un usuario
    Body JSON:
    {
        "activo": boolean
    }
    """
    try:
        data = request.get_json()
        nuevo_estado = data.get('activo', False)
        
        supabase = current_app.config['SUPABASE']
        
        # Verificar que el usuario existe
        usuario = supabase.table('usuarios').select('nombre').eq('id', id).single().execute().data
        if not usuario:
            return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
        
        # Actualizar estado
        supabase.table('usuarios').update({'activo': nuevo_estado}).eq('id', id).execute()
        
        return jsonify({
            "success": True,
            "message": f"Usuario {'activado' if nuevo_estado else 'desactivado'} correctamente"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en toggle_estado_usuario: {str(e)}")
        return jsonify({"success": False, "message": f"Error al cambiar estado: {str(e)}"}), 500


@bp.route("/toggle-bloqueo/<int:id>", methods=["POST"])
@token_required
def toggle_bloqueo_usuario(current_user, id):
    """
    Bloquea o desbloquea un usuario
    Body JSON:
    {
        "bloqueado": boolean
    }
    """
    try:
        data = request.get_json()
        bloqueado = data.get('bloqueado', False)
        
        supabase = current_app.config['SUPABASE']
        
        # Verificar que el usuario existe
        usuario = supabase.table('usuarios').select('nombre').eq('id', id).single().execute().data
        if not usuario:
            return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
        
        # Actualizar estado de bloqueo y resetear intentos fallidos si se desbloquea
        update_data = {
            'bloqueado': bloqueado,
            'intentos_fallidos': 0 if not bloqueado else None
        }
        
        # Eliminar None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        supabase.table('usuarios').update(update_data).eq('id', id).execute()
        
        return jsonify({
            "success": True,
            "message": f"Usuario {'bloqueado' if bloqueado else 'desbloqueado'} correctamente"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en toggle_bloqueo_usuario: {str(e)}")
        return jsonify({"success": False, "message": f"Error al cambiar bloqueo: {str(e)}"}), 500


@bp.route("/toggle-modulo/<int:id>", methods=["POST"])
@token_required
def toggle_modulo_permiso(current_user, id):
    """
    Otorga o revoca permiso de un módulo a un usuario
    Body JSON:
    {
        "modulo_id": int,
        "permitir": boolean
    }
    """
    try:
        data = request.get_json()
        modulo_id = int(data.get('modulo_id'))
        permitir = data.get('permitir', False)
        
        supabase = current_app.config['SUPABASE']
        
        # Verificar si ya existe el permiso
        existe = supabase.table('usuario_modulo').select('id').eq(
            'usuario_id', id
        ).eq('modulo_id', modulo_id).execute().data
        
        if permitir:
            if not existe:
                # Agregar permiso
                supabase.table('usuario_modulo').insert({
                    'usuario_id': id,
                    'modulo_id': modulo_id
                }).execute()
                return jsonify({"success": True, "message": "Permiso otorgado"})
            else:
                return jsonify({"success": True, "message": "El permiso ya existía"})
        else:
            if existe:
                # Quitar permiso
                supabase.table('usuario_modulo').delete().eq(
                    'usuario_id', id
                ).eq('modulo_id', modulo_id).execute()
                return jsonify({"success": True, "message": "Permiso revocado"})
            else:
                return jsonify({"success": True, "message": "El permiso ya estaba revocado"})
        
    except Exception as e:
        current_app.logger.error(f"Error en toggle_modulo_permiso: {str(e)}")
        return jsonify({"success": False, "message": f"Error al cambiar permiso: {str(e)}"}), 500


# ================================================================
# ENDPOINTS DE GESTIÓN DE CONTRASEÑAS
# ================================================================

@bp.route("/reset-password/<int:id>", methods=["POST"])
@token_required
def reset_password_usuario(current_user, id):
    """
    Genera una contraseña temporal para el usuario
    Retorna la contraseña temporal para que pueda ser comunicada al usuario
    """
    try:
        supabase = current_app.config['SUPABASE']
        
        # Obtener usuario
        usuario = supabase.table('usuarios').select('nombre, email').eq('id', id).single().execute().data
        if not usuario:
            return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
        
        # Generar contraseña temporal
        password_temp = generar_password_temporal()
        hashed = generate_password_hash(password_temp)
        
        # Actualizar contraseña y marcar como temporal
        supabase.table('usuarios').update({
            'password': hashed,
            'intentos_fallidos': 0,
            'bloqueado': False,
            'motivo_bloqueo': 'CONTRASEÑA_TEMPORAL'
        }).eq('id', id).execute()
        
        return jsonify({
            "success": True,
            "message": "Contraseña temporal generada correctamente",
            "password_temporal": password_temp,
            "usuario": usuario['nombre'],
            "email": usuario['email']
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en reset_password_usuario: {str(e)}")
        return jsonify({"success": False, "message": f"Error al resetear contraseña: {str(e)}"}), 500


@bp.route("/change-password", methods=["POST"])
@token_required
def change_password(current_user):
    """
    Permite al usuario cambiar su propia contraseña
    Body JSON:
    {
        "current_password": "string",
        "new_password": "string",
        "confirm_password": "string"
    }
    """
    try:
        data = request.get_json()
        
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')
        
        # Validaciones
        if not current_password or not new_password or not confirm_password:
            return jsonify({
                "success": False,
                "message": "Todos los campos son requeridos"
            }), 400
        
        if new_password != confirm_password:
            return jsonify({
                "success": False,
                "message": "Las contraseñas no coinciden"
            }), 400
        
        # Validar nueva contraseña
        password_valido, password_error = validar_password(new_password)
        if not password_valido:
            return jsonify({"success": False, "message": password_error}), 400
        
        supabase = current_app.config['SUPABASE']
        
        # Obtener usuario actual
        usuario = supabase.table('usuarios').select('password, motivo_bloqueo').eq(
            'id', current_user.id
        ).single().execute().data
        
        if not usuario:
            return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
        
        # Verificar contraseña actual
        if not check_password_hash(usuario['password'], current_password):
            return jsonify({
                "success": False,
                "message": "La contraseña actual es incorrecta"
            }), 401
        
        # Actualizar contraseña y limpiar marca de temporal
        hashed_new = generate_password_hash(new_password)
        supabase.table('usuarios').update({
            'password': hashed_new,
            'motivo_bloqueo': None
        }).eq('id', current_user.id).execute()
        
        return jsonify({
            "success": True,
            "message": "Contraseña actualizada correctamente"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en change_password: {str(e)}")
        return jsonify({"success": False, "message": f"Error al cambiar contraseña: {str(e)}"}), 500


# ================================================================
# ENDPOINTS AUXILIARES
# ================================================================

@bp.route("/modulos", methods=["GET"])
@token_required
def api_get_modulos(current_user):
    """
    Obtiene la lista de todos los módulos disponibles para asignación
    """
    try:
        supabase = current_app.config['SUPABASE']
        
        modulos = supabase.table('modulos').select('*').order('nombre_modulo').execute().data or []
        
        return jsonify({
            "success": True,
            "data": modulos
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en api_get_modulos: {str(e)}")
        return jsonify({"success": False, "message": f"Error al obtener módulos: {str(e)}"}), 500


@bp.route("/check-temp-password", methods=["GET"])
@token_required
def check_temp_password(current_user):
    """
    Verifica si el usuario tiene una contraseña temporal
    """
    try:
        supabase = current_app.config['SUPABASE']
        
        usuario = supabase.table('usuarios').select('motivo_bloqueo').eq(
            'id', current_user.id
        ).single().execute().data
        
        if usuario and usuario.get('motivo_bloqueo') == 'CONTRASEÑA_TEMPORAL':
            return jsonify({"temp_password": True})
        
        return jsonify({"temp_password": False})
        
    except Exception as e:
        current_app.logger.error(f"Error en check_temp_password: {str(e)}")
        return jsonify({"temp_password": False})
