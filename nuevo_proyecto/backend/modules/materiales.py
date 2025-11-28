"""
Módulo de materiales adaptado para trabajar con frontend React
Mantiene compatibilidad con estructura existente
"""

from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required

bp = Blueprint("materiales", __name__)


@bp.route("/api/todos", methods=["GET"])
@token_required
def api_get_materiales(current_user):
    """
    Devuelve lista de todos los materiales en formato JSON.
    """
    try:
        supabase = current_app.config['SUPABASE']
        
        response = supabase.table("materiales").select("*").order("material").execute()
        
        materiales = response.data or []
        
        return jsonify({
            "success": True,
            "data": materiales
        })
        
    except Exception as e:
        current_app.logger.error(f"Error en API de materiales: {str(e)}")
        return jsonify({"success": False, "message": "Error al obtener los materiales"}), 500


@bp.route("/api/items", methods=["GET"])
@token_required
def api_get_items(current_user):
    """
    Devuelve lista de items (tipos) disponibles para selección.
    """
    try:
        supabase = current_app.config['SUPABASE']
        
        response = supabase.table("item").select("tipo").order("tipo", desc=False).execute()
        
        items = response.data or []
        
        return jsonify({
            "success": True,
            "data": items
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener items: {str(e)}")
        return jsonify({"success": False, "message": "Error al obtener items"}), 500


@bp.route("/new", methods=["POST"])
@token_required
def new_material(current_user):
    """Crea un nuevo material"""
    try:
        data = request.get_json() or {}
        
        # Validar y limpiar datos de entrada
        cod = data.get("cod", "").strip().upper()
        material = data.get("material", "").strip().upper()
        tipo = data.get("tipo", "").strip().upper()
        item = data.get("item", "").strip().upper()
        
        # Validaciones básicas
        if not cod:
            return jsonify({"success": False, "message": "El código es obligatorio"}), 400
        
        if not material:
            return jsonify({"success": False, "message": "El nombre del material es obligatorio"}), 400
        
        if not item:
            return jsonify({"success": False, "message": "El item es obligatorio"}), 400
        
        supabase = current_app.config['SUPABASE']
        
        # Verificar duplicado de código
        dup = supabase.table("materiales").select("id").eq("cod", cod).execute().data
        
        if dup:
            return jsonify({"success": False, "message": f"El código '{cod}' ya está registrado"}), 400
        
        # Preparar payload
        payload = {
            "cod": cod,
            "material": material,
            "tipo": tipo if tipo else None,
            "item": item
        }
        
        # Insertar material
        result = supabase.table("materiales").insert(payload).execute()
        
        if result.data:
            current_app.logger.info(f"Material creado: {material} (cod: {cod})")
            
            # Invalidar cache si existe
            try:
                from backend.utils.cache import clear_cache
                clear_cache("materiales")
            except:
                pass
            
            return jsonify({
                "success": True,
                "data": result.data[0] if isinstance(result.data, list) else result.data,
                "message": f"Material '{material}' creado exitosamente"
            })
        else:
            return jsonify({"success": False, "message": "Error al crear el material"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error al crear material: {str(e)}")
        return jsonify({"success": False, "message": "Error interno al crear el material"}), 500


@bp.route("/edit/<int:id>", methods=["GET", "POST"])
@token_required
def edit_material(id, current_user):
    """Edita un material existente"""
    supabase = current_app.config['SUPABASE']
    
    try:
        # Obtener material actual
        material = supabase.table("materiales").select("*").eq("id", id).execute().data
        if not material:
            return jsonify({"success": False, "message": "Material no encontrado"}), 404
        
        material = material[0]
        
        if request.method == 'GET':
            return jsonify({"success": True, "data": material})
        
        # POST - actualizar
        data = request.get_json() or {}
        
        # Validar y limpiar datos
        cod = data.get("cod", "").strip().upper()
        material_name = data.get("material", "").strip().upper()
        tipo = data.get("tipo", "").strip().upper()
        item = data.get("item", "").strip().upper()
        
        if not cod:
            return jsonify({"success": False, "message": "El código es obligatorio"}), 400
        
        if not material_name:
            return jsonify({"success": False, "message": "El nombre del material es obligatorio"}), 400
        
        if not item:
            return jsonify({"success": False, "message": "El item es obligatorio"}), 400
        
        # Verificar duplicado de código (excluyendo el actual)
        if cod != material["cod"]:
            dup = supabase.table("materiales").select("id").eq("cod", cod).execute().data
            if dup and any(d.get('id') != id for d in dup):
                return jsonify({"success": False, "message": f"Ya existe otro material con el código '{cod}'"}), 400
        
        # Preparar payload
        payload = {
            "cod": cod,
            "material": material_name,
            "tipo": tipo if tipo else None,
            "item": item
        }
        
        # Actualizar material
        result = supabase.table("materiales").update(payload).eq("id", id).execute()
        
        if result.data:
            current_app.logger.info(f"Material actualizado: {material_name} (ID: {id})")
            
            # Invalidar cache si existe
            try:
                from backend.utils.cache import clear_cache
                clear_cache("materiales")
            except:
                pass
            
            return jsonify({
                "success": True,
                "data": result.data[0] if isinstance(result.data, list) else result.data,
                "message": f"Material '{material_name}' actualizado exitosamente"
            })
        else:
            return jsonify({"success": False, "message": "Error al actualizar el material"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error al editar material ID {id}: {str(e)}")
        return jsonify({"success": False, "message": "Error interno al procesar el material"}), 500


@bp.route("/api/search", methods=["GET"])
@token_required
def api_search(current_user):
    """API para búsqueda de materiales (para select/autocomplete)"""
    try:
        term = request.args.get("term", "").strip()
        
        if not term:
            return jsonify({"results": []})
        
        supabase = current_app.config['SUPABASE']
        materiales = (
            supabase.table("materiales")
            .select("id, cod, material")
            .or_(f"cod.ilike.%{term}%,material.ilike.%{term}%")
            .limit(20)
            .execute()
            .data or []
        )
        
        results = [{"id": m["id"], "text": f"{m['cod']} - {m['material']}"} for m in materiales]
        return jsonify({"results": results})
        
    except Exception as e:
        current_app.logger.error(f"Error en búsqueda de materiales: {e}")
        return jsonify({"results": []})
