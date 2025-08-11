from flask import Blueprint, request, jsonify, current_app, render_template

bp_correo = Blueprint('correo', __name__)

# Vista HTML para gestión de correos
@bp_correo.route('/correos', methods=['GET'])
def vista_correos():
    return render_template('correo.html')

# Listar correos
@bp_correo.route('/api/correos', methods=['GET'])
def listar_correos():
    try:
        supabase = current_app.config["SUPABASE"]
        response = supabase.table("correos_destinatarios").select("id, nombre, correo, activo").execute()
        
        if hasattr(response, 'error') and response.error:
            return jsonify({"success": False, "msg": str(response.error)}), 500
            
        correos = response.data or []
        return jsonify(correos)
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500

# Crear correo
@bp_correo.route('/api/correos', methods=['POST'])
def crear_correo():
    try:
        supabase = current_app.config["SUPABASE"]
        data = request.json
        nombre = data.get('nombre')
        correo = data.get('correo')
        activo = data.get('activo', True)
        
        if not nombre or not correo:
            return jsonify({"success": False, "msg": "Nombre y correo son requeridos."}), 400
        
        result = supabase.table("correos_destinatarios").insert({
            "nombre": nombre, 
            "correo": correo, 
            "activo": activo
        }).execute()
        
        if hasattr(result, 'error') and result.error:
            return jsonify({"success": False, "msg": str(result.error)}), 500
        
        return jsonify({"success": True, "msg": "Correo creado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500

# Editar correo
@bp_correo.route('/api/correos/<int:correo_id>', methods=['PUT'])
def editar_correo(correo_id):
    try:
        supabase = current_app.config["SUPABASE"]
        data = request.json
        nombre = data.get('nombre')
        correo = data.get('correo')
        activo = data.get('activo')
        
        update_data = {}
        if nombre is not None:
            update_data['nombre'] = nombre
        if correo is not None:
            update_data['correo'] = correo
        if activo is not None:
            update_data['activo'] = activo
        
        if not update_data:
            return jsonify({"success": False, "msg": "No hay datos para actualizar."}), 400
        
        result = supabase.table("correos_destinatarios").update(update_data).eq("id", correo_id).execute()
        
        if hasattr(result, 'error') and result.error:
            return jsonify({"success": False, "msg": str(result.error)}), 500
        
        # Verificar si se actualizó algún registro
        if not result.data:
            return jsonify({"success": False, "msg": "No se encontró el registro para actualizar."}), 404
            
        return jsonify({"success": True, "msg": "Correo actualizado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500

# Eliminar correo
@bp_correo.route('/api/correos/<int:correo_id>', methods=['DELETE'])
def eliminar_correo(correo_id):
    try:
        supabase = current_app.config["SUPABASE"]
        
        # Primero verificar si el registro existe
        check_result = supabase.table("correos_destinatarios").select("id").eq("id", correo_id).execute()
        
        if not check_result.data:
            return jsonify({"success": False, "msg": "El destinatario no existe."}), 404
        
        # Proceder con la eliminación
        result = supabase.table("correos_destinatarios").delete().eq("id", correo_id).execute()
        
        if hasattr(result, 'error') and result.error:
            return jsonify({"success": False, "msg": str(result.error)}), 500
        
        # Verificar si se eliminó el registro
        if not result.data:
            return jsonify({"success": False, "msg": "No se pudo eliminar el destinatario."}), 500
            
        return jsonify({"success": True, "msg": "Correo eliminado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500