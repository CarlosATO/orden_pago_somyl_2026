"""
Backend API para módulo de Presupuestos
Maneja CRUD de presupuestos por proyecto
"""
from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required
from datetime import datetime

bp = Blueprint("presupuestos", __name__)

# ==================== ENDPOINTS ====================

@bp.route("/", methods=["POST"])
@token_required
def create_presupuesto(current_user):
    """
    Crear nuevo presupuesto
    Body: {proyecto_id, item, detalle, fecha, monto}
    """
    data = request.get_json()
    
    if not data or not all(k in data for k in ['proyecto_id', 'item', 'fecha', 'monto']):
        return jsonify({"success": False, "message": "Faltan datos requeridos"}), 400
    
    supabase = current_app.config['SUPABASE']
    
    try:
        # Preparar datos
        nuevo_presupuesto = {
            "proyecto_id": int(data['proyecto_id']),
            "item": str(data['item']).strip(),
            "detalle": data.get('detalle', '').strip() if data.get('detalle') else None,
            "fecha": data['fecha'],
            "monto": int(float(data['monto']))
        }
        
        # Validar monto positivo
        if nuevo_presupuesto['monto'] <= 0:
            return jsonify({"success": False, "message": "El monto debe ser mayor a cero"}), 400
        
        # Insertar en Supabase
        result = supabase.table("presupuesto").insert(nuevo_presupuesto).execute()
        
        if result.data:
            return jsonify({
                "success": True,
                "message": "Presupuesto registrado exitosamente",
                "presupuesto": result.data[0]
            }), 201
        else:
            return jsonify({"success": False, "message": "Error al registrar presupuesto"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error al crear presupuesto: {e}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/gastos/<int:proyecto_id>", methods=["GET"])
@token_required
def get_gastos_proyecto(current_user, proyecto_id):
    """
    Obtener todos los gastos de un proyecto específico
    Incluye estadísticas
    """
    supabase = current_app.config['SUPABASE']
    
    try:
        # Obtener gastos del proyecto con paginación manual
        page_size = 1000
        offset = 0
        gastos = []
        
        while True:
            batch = (
                supabase.table("presupuesto")
                .select("id, proyecto_id, item, detalle, fecha, monto")
                .eq("proyecto_id", proyecto_id)
                .order("fecha", desc=True)
                .range(offset, offset + page_size - 1)
                .execute()
                .data or []
            )
            gastos.extend(batch)
            
            if len(batch) < page_size:
                break
            offset += page_size
        
        # Calcular estadísticas
        total_amount = sum(g.get("monto", 0) for g in gastos)
        unique_items = len(set(g.get("item") for g in gastos if g.get("item")))
        last_entry = gastos[0].get("fecha") if gastos else None
        
        # Formatear fecha de último registro
        if last_entry:
            try:
                last_entry_date = datetime.fromisoformat(last_entry)
                last_entry = last_entry_date.strftime("%d/%m/%Y")
            except:
                pass
        
        stats = {
            "total_entries": len(gastos),
            "total_amount": total_amount,
            "unique_items": unique_items,
            "last_entry": last_entry
        }
        
        return jsonify({
            "success": True,
            "gastos": gastos,
            "stats": stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener gastos: {e}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/<int:presupuesto_id>", methods=["DELETE"])
@token_required
def delete_presupuesto(current_user, presupuesto_id):
    """
    Eliminar un presupuesto por ID
    """
    supabase = current_app.config['SUPABASE']
    
    try:
        result = supabase.table("presupuesto").delete().eq("id", presupuesto_id).execute()
        
        if result.data:
            return jsonify({
                "success": True,
                "message": "Presupuesto eliminado exitosamente"
            })
        else:
            return jsonify({"success": False, "message": "Presupuesto no encontrado"}), 404
            
    except Exception as e:
        current_app.logger.error(f"Error al eliminar presupuesto: {e}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/<int:presupuesto_id>", methods=["PUT"])
@token_required
def update_presupuesto(current_user, presupuesto_id):
    """
    Actualizar un presupuesto existente
    Body: {item, detalle, fecha, monto}
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "message": "No se enviaron datos"}), 400
    
    supabase = current_app.config['SUPABASE']
    
    try:
        # Preparar datos de actualización
        update_data = {}
        
        if 'item' in data:
            update_data['item'] = str(data['item']).strip()
        if 'detalle' in data:
            update_data['detalle'] = data['detalle'].strip() if data['detalle'] else None
        if 'fecha' in data:
            update_data['fecha'] = data['fecha']
        if 'monto' in data:
            monto = int(float(data['monto']))
            if monto <= 0:
                return jsonify({"success": False, "message": "El monto debe ser mayor a cero"}), 400
            update_data['monto'] = monto
        
        if not update_data:
            return jsonify({"success": False, "message": "No hay datos para actualizar"}), 400
        
        # Actualizar en Supabase
        result = supabase.table("presupuesto").update(update_data).eq("id", presupuesto_id).execute()
        
        if result.data:
            return jsonify({
                "success": True,
                "message": "Presupuesto actualizado exitosamente",
                "presupuesto": result.data[0]
            })
        else:
            return jsonify({"success": False, "message": "Presupuesto no encontrado"}), 404
            
    except Exception as e:
        current_app.logger.error(f"Error al actualizar presupuesto: {e}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
