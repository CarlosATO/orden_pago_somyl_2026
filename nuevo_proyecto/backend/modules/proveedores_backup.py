from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required

bp = Blueprint("proveedores", __name__)

@bp.route("/<int:proveedor_id>", methods=["GET"])
@token_required
def get_proveedor(current_user, proveedor_id):
    """
    Obtiene los datos de un proveedor específico.
    """
    supabase = current_app.config['SUPABASE']
    try:
        response = supabase.table("proveedores").select("*").eq("id", proveedor_id).single().execute()
        
        if response.data:
            return jsonify({
                "success": True,
                "id": response.data.get('id'),
                "nombre": response.data.get('nombre'),
                "rut": response.data.get('rut'),
                "email": response.data.get('email'),
                "telefono": response.data.get('telefono')
            })
        else:
            return jsonify({"success": False, "message": "Proveedor no encontrado"}), 404
            
    except Exception as e:
        current_app.logger.error(f"Error al obtener proveedor {proveedor_id}: {str(e)}")
        return jsonify({"success": False, "message": "Error al obtener datos del proveedor"}), 500

@bp.route("/", methods=["GET"])
@token_required
def get_proveedores(current_user):
    """
    Obtiene la lista de todos los proveedores.
    """
    supabase = current_app.config['SUPABASE']
    try:
        response = supabase.table("proveedores").select("id, nombre, rut").execute()

        proveedores = []
        for prov in response.data:
            proveedores.append({
                "id": prov.get('id'),
                "nombre": prov.get('nombre'),
                "rut": prov.get('rut')
            })

        return jsonify({
            "success": True,
            "data": proveedores
        })

    except Exception as e:
        current_app.logger.error(f"Error al obtener proveedores: {str(e)}")
        return jsonify({"success": False, "message": "Error al obtener lista de proveedores"}), 500
