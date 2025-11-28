"""
Módulo de items adaptado para trabajar con frontend React
Mantiene compatibilidad con estructura existente
"""

from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required

bp = Blueprint("items", __name__)


@bp.route("/", methods=["GET"])
@token_required
def get_items(current_user):
    """
    Devuelve lista de todos los items en formato JSON.
    Endpoint principal para obtener items
    """
    try:
        supabase = current_app.config['SUPABASE']
        
        response = supabase.table("item").select("*").order("tipo", desc=False).execute()
        
        items = response.data or []
        
        return jsonify({
            "success": True,
            "items": items
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener items: {str(e)}")
        return jsonify({"success": False, "message": "Error al obtener los items"}), 500


@bp.route("/todos", methods=["GET"])
@token_required
def api_get_items(current_user):
    """
    Devuelve lista de todos los items en formato JSON.
    """
    try:
        supabase = current_app.config['SUPABASE']
        
        response = supabase.table("item").select("*").order("tipo", desc=False).execute()
        
        items = response.data or []
        
        return jsonify({
            "success": True,
            "count": len(items),
            "data": items
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en API de items: {str(e)}")
        return jsonify({"success": False, "message": "Error al obtener los items"}), 500


@bp.route("/new", methods=["POST"])
@token_required
def new_item(current_user):
    """
    Crea un nuevo item.
    """
    try:
        data = request.get_json()
        tipo = data.get("tipo", "").strip().upper()
        
        if not tipo:
            return jsonify({"success": False, "message": "Debe ingresar un nombre de item"}), 400
        
        supabase = current_app.config['SUPABASE']
        
        # Verificar duplicado
        existe = supabase.table("item").select("id").eq("tipo", tipo).execute().data
        
        if existe:
            return jsonify({"success": False, "message": "Este item ya está registrado"}), 400
        
        # Insertar
        result = supabase.table("item").insert({"tipo": tipo}).execute()
        
        if result.data:
            return jsonify({
                "success": True,
                "message": "Item creado exitosamente",
                "data": result.data[0]
            })
        else:
            return jsonify({"success": False, "message": "Error al crear item"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error al crear item: {str(e)}")
        return jsonify({"success": False, "message": "Error al crear item"}), 500


@bp.route("/edit/<int:id>", methods=["POST"])
@token_required
def edit_item(current_user, id):
    """
    Actualiza un item existente.
    """
    try:
        data = request.get_json()
        tipo_new = data.get("tipo", "").strip().upper()
        
        if not tipo_new:
            return jsonify({"success": False, "message": "Debe ingresar un nombre de item"}), 400
        
        supabase = current_app.config['SUPABASE']
        
        # Verificar que el item existe
        item_actual = supabase.table("item").select("*").eq("id", id).execute().data
        
        if not item_actual:
            return jsonify({"success": False, "message": "Item no encontrado"}), 404
        
        item = item_actual[0]
        
        # Si cambió el nombre, verificar duplicado
        if tipo_new != item["tipo"]:
            dup = supabase.table("item").select("id").eq("tipo", tipo_new).execute().data
            
            if dup:
                return jsonify({"success": False, "message": "Este item ya está registrado"}), 400
        
        # Actualizar
        result = supabase.table("item").update({"tipo": tipo_new}).eq("id", id).execute()
        
        if result.data:
            return jsonify({
                "success": True,
                "message": "Item actualizado exitosamente",
                "data": result.data[0]
            })
        else:
            return jsonify({"success": False, "message": "Error al actualizar item"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error al actualizar item: {str(e)}")
        return jsonify({"success": False, "message": "Error al actualizar item"}), 500


@bp.route("/search", methods=["GET"])
@token_required
def api_search_items(current_user):
    """
    Búsqueda de items por término.
    """
    try:
        term = request.args.get("q", "").strip()
        
        if not term:
            return jsonify({"success": True, "data": []})
        
        supabase = current_app.config['SUPABASE']
        
        items = supabase.table("item") \
            .select("*") \
            .ilike("tipo", f"%{term}%") \
            .order("tipo") \
            .limit(20) \
            .execute() \
            .data or []
        
        return jsonify({"success": True, "data": items})
        
    except Exception as e:
        current_app.logger.error(f"Error en búsqueda de items: {str(e)}")
        return jsonify({"success": False, "data": []}), 500