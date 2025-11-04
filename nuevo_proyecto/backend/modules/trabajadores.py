"""
Módulo de trabajadores adaptado para trabajar con frontend React
Mantiene compatibilidad con estructura existente
"""

from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required
import re

bp = Blueprint("trabajadores", __name__)


def validar_email(email):
    """Valida el formato del email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validar_nombre(nombre):
    """Valida el formato del nombre"""
    if not nombre or len(nombre.strip()) < 2:
        return False, "El nombre debe tener al menos 2 caracteres"
    if len(nombre.strip()) > 100:
        return False, "El nombre no puede exceder 100 caracteres"
    return True, ""


@bp.route("/todos", methods=["GET"])
@token_required
def api_get_trabajadores(current_user):
    """
    Devuelve lista de todos los trabajadores en formato JSON.
    """
    try:
        supabase = current_app.config['SUPABASE']
        
        response = supabase.table("trabajadores").select("*").order("nombre").execute()
        
        trabajadores = response.data or []
        
        return jsonify({
            "success": True,
            "count": len(trabajadores),
            "data": trabajadores
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en API de trabajadores: {str(e)}")
        return jsonify({"success": False, "message": "Error al obtener los trabajadores"}), 500


# Nuevo endpoint: obtener trabajador por id
@bp.route("/<int:id>", methods=["GET"])
@token_required
def api_get_trabajador_by_id(current_user, id):
    """
    Devuelve los datos de un trabajador por id (incluye correo).
    """
    try:
        supabase = current_app.config['SUPABASE']
        trabajador = supabase.table("trabajadores").select("id, nombre, correo").eq("id", id).execute().data
        if not trabajador:
            return jsonify({"message": "Trabajador no encontrado"}), 404
        # Devolver directamente el objeto trabajador para compatibilidad con el frontend
        return jsonify(trabajador[0])
    except Exception as e:
        current_app.logger.error(f"Error al obtener trabajador por id: {str(e)}")
        return jsonify({"success": False, "message": "Error al obtener trabajador"}), 500


@bp.route("/new", methods=["POST"])
@token_required
def new_trabajador(current_user):
    """
    Crea un nuevo trabajador.
    """
    try:
        data = request.get_json()
        nombre = data.get("nombre", "").strip().upper()
        correo = data.get("correo", "").strip().lower()
        
        # Validaciones
        if not nombre or not correo:
            return jsonify({"success": False, "message": "Todos los campos son obligatorios"}), 400
        
        # Validar nombre
        nombre_valido, nombre_error = validar_nombre(nombre)
        if not nombre_valido:
            return jsonify({"success": False, "message": nombre_error}), 400
        
        # Validar email
        if not validar_email(correo):
            return jsonify({"success": False, "message": "El formato del correo electrónico no es válido"}), 400
        
        supabase = current_app.config['SUPABASE']
        
        # Verificar duplicado por correo (bloqueo)
        dup_correo = supabase.table("trabajadores").select("id, nombre").eq("correo", correo).execute().data
        
        if dup_correo:
            return jsonify({
                "success": False, 
                "message": f"El correo ya está registrado para el trabajador: {dup_correo[0]['nombre']}"
            }), 400
        
        # Verificar duplicado por nombre (advertencia, no bloqueo)
        dup_nombre = supabase.table("trabajadores").select("id, correo").eq("nombre", nombre).execute().data
        
        warning_message = None
        if dup_nombre:
            warning_message = f"Ya existe un trabajador con el nombre '{nombre}' (correo: {dup_nombre[0]['correo']}). Se creará de todas formas."
        
        # Crear
        payload = {
            "nombre": nombre,
            "correo": correo
        }
        
        result = supabase.table("trabajadores").insert(payload).execute()
        
        if result.data:
            response_data = {
                "success": True,
                "message": "Trabajador creado exitosamente",
                "data": result.data[0]
            }
            
            if warning_message:
                response_data["warning"] = True
                response_data["message"] = warning_message
            
            return jsonify(response_data)
        else:
            return jsonify({"success": False, "message": "Error al crear trabajador"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error al crear trabajador: {str(e)}")
        return jsonify({"success": False, "message": "Error al crear trabajador"}), 500


@bp.route("/edit/<int:id>", methods=["POST"])
@token_required
def edit_trabajador(current_user, id):
    """
    Actualiza un trabajador existente.
    """
    try:
        data = request.get_json()
        nombre_new = data.get("nombre", "").strip().upper()
        correo_new = data.get("correo", "").strip().lower()
        
        # Validaciones
        if not nombre_new or not correo_new:
            return jsonify({"success": False, "message": "Todos los campos son obligatorios"}), 400
        
        # Validar nombre
        nombre_valido, nombre_error = validar_nombre(nombre_new)
        if not nombre_valido:
            return jsonify({"success": False, "message": nombre_error}), 400
        
        # Validar email
        if not validar_email(correo_new):
            return jsonify({"success": False, "message": "El formato del correo electrónico no es válido"}), 400
        
        supabase = current_app.config['SUPABASE']
        
        # Verificar que el trabajador existe
        trabajador_actual = supabase.table("trabajadores").select("*").eq("id", id).execute().data
        
        if not trabajador_actual:
            return jsonify({"success": False, "message": "Trabajador no encontrado"}), 404
        
        trabajador = trabajador_actual[0]
        
        # Si cambió el correo, verificar duplicado (bloqueo)
        if correo_new != trabajador["correo"]:
            dup_correo = supabase.table("trabajadores").select("id, nombre").eq("correo", correo_new).execute().data
            
            if dup_correo:
                return jsonify({
                    "success": False,
                    "message": f"El correo ya está registrado para el trabajador: {dup_correo[0]['nombre']}"
                }), 400
        
        # Si cambió el nombre, verificar duplicado (advertencia, no bloqueo)
        warning_message = None
        if nombre_new != trabajador["nombre"]:
            dup_nombre = supabase.table("trabajadores").select("id, correo").eq("nombre", nombre_new).execute().data
            
            if dup_nombre:
                warning_message = f"Ya existe un trabajador con el nombre '{nombre_new}' (correo: {dup_nombre[0]['correo']}). Se actualizará de todas formas."
        
        # Actualizar
        payload = {
            "nombre": nombre_new,
            "correo": correo_new
        }
        
        result = supabase.table("trabajadores").update(payload).eq("id", id).execute()
        
        if result.data:
            response_data = {
                "success": True,
                "message": "Trabajador actualizado exitosamente",
                "data": result.data[0]
            }
            
            if warning_message:
                response_data["warning"] = True
                response_data["message"] = warning_message
            
            return jsonify(response_data)
        else:
            return jsonify({"success": False, "message": "Error al actualizar trabajador"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error al actualizar trabajador: {str(e)}")
        return jsonify({"success": False, "message": "Error al actualizar trabajador"}), 500


@bp.route("/search", methods=["GET"])
@token_required
def api_search_trabajadores(current_user):
    """
    Búsqueda de trabajadores por término.
    """
    try:
        term = request.args.get("q", "").strip()
        
        if not term:
            return jsonify({"success": True, "data": []})
        
        supabase = current_app.config['SUPABASE']
        
        # Buscar por nombre o correo
        trabajadores = supabase.table("trabajadores") \
            .select("*") \
            .or_(f"nombre.ilike.%{term}%,correo.ilike.%{term}%") \
            .order("nombre") \
            .limit(20) \
            .execute() \
            .data or []
        
        return jsonify({"success": True, "data": trabajadores})
        
    except Exception as e:
        current_app.logger.error(f"Error en búsqueda de trabajadores: {str(e)}")
        return jsonify({"success": False, "data": []}), 500
