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
    Crear uno o múltiples presupuestos
    Body: {proyecto_id, lineas: [{item, detalle, fecha, monto}, ...]}
    O Body: {proyecto_id, item, detalle, fecha, monto} (compatibilidad)
    """
    data = request.get_json()
    
    if not data or 'proyecto_id' not in data:
        return jsonify({"success": False, "message": "proyecto_id es requerido"}), 400
    
    supabase = current_app.config['SUPABASE']
    proyecto_id = int(data['proyecto_id'])
    
    try:
        # Obtener nombre del proyecto UNA SOLA VEZ
        proyecto_result = (
            supabase.table("proyectos")
            .select("proyecto")
            .eq("id", proyecto_id)
            .limit(1)
            .execute()
        )
        
        if not proyecto_result.data or len(proyecto_result.data) == 0:
            return jsonify({"success": False, "message": "Proyecto no encontrado"}), 404
        
        proyecto_nombre = proyecto_result.data[0]['proyecto']
        
        # Detectar si es una línea única o múltiples líneas
        if 'lineas' in data:
            # Modo batch: múltiples líneas
            lineas = data['lineas']
        else:
            # Modo compatible: una sola línea
            if not all(k in data for k in ['item', 'fecha', 'monto']):
                return jsonify({"success": False, "message": "Faltan datos requeridos"}), 400
            lineas = [{
                'item': data['item'],
                'detalle': data.get('detalle', ''),
                'fecha': data['fecha'],
                'monto': data['monto']
            }]
        
        # Preparar todas las líneas para inserción
        registros_a_insertar = []
        
        for linea in lineas:
            # Validar campos requeridos
            if not all(k in linea for k in ['item', 'fecha', 'monto']):
                continue
            
            # Parsear fecha para extraer mes y año
            fecha_obj = datetime.strptime(linea['fecha'], '%Y-%m-%d')
            mes_numero = fecha_obj.month
            anio = fecha_obj.year
            
            # Nombres de meses en inglés
            meses = ["January", "February", "March", "April", "May", "June",
                     "July", "August", "September", "October", "November", "December"]
            mes_nombre = meses[mes_numero - 1]
            
            monto = int(float(linea['monto']))
            
            # Validar monto positivo
            if monto <= 0:
                continue
            
            # Preparar registro completo
            registro = {
                "proyecto_id": proyecto_id,
                "proyecto": proyecto_nombre,
                "item": str(linea['item']).strip(),
                "detalle": linea.get('detalle', '').strip() if linea.get('detalle') else '',
                "fecha": linea['fecha'],
                "monto": monto,
                "mes_numero": mes_numero,
                "mes_nombre": mes_nombre,
                "anio": anio,
                "creado_por": current_user.id if current_user and hasattr(current_user, 'id') else None
            }
            
            registros_a_insertar.append(registro)
        
        if len(registros_a_insertar) == 0:
            return jsonify({"success": False, "message": "No hay registros válidos para insertar"}), 400
        
        # Insertar TODOS los registros en Supabase de una vez
        result = supabase.table("presupuesto").insert(registros_a_insertar).execute()
        
        if result.data:
            current_app.logger.info(f"✓ {len(result.data)} presupuesto(s) creado(s) para {proyecto_nombre}")
            return jsonify({
                "success": True,
                "message": f"{len(result.data)} presupuesto(s) registrado(s) exitosamente",
                "presupuestos": result.data
            }), 201
        else:
            return jsonify({"success": False, "message": "Error al registrar presupuestos"}), 500
            
    except ValueError as ve:
        current_app.logger.error(f"Error de validación: {ve}")
        return jsonify({"success": False, "message": f"Error de validación: {str(ve)}"}), 400
    except Exception as e:
        current_app.logger.error(f"Error al crear presupuesto: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/totales", methods=["GET"])
@token_required
def get_totales_proyectos(current_user):
    """
    Obtener totales agregados de presupuesto para TODOS los proyectos activos
    Optimizado para carga inicial rápida
    """
    supabase = current_app.config['SUPABASE']
    
    try:
        # Obtener TODOS los registros de presupuesto de una vez
        all_presupuestos = (
            supabase.table("presupuesto")
            .select("proyecto_id, monto")
            .execute()
            .data or []
        )
        
        # Agregar por proyecto_id en memoria (mucho más rápido)
        totales_por_proyecto = {}
        for registro in all_presupuestos:
            proyecto_id = registro.get("proyecto_id")
            monto = registro.get("monto", 0)
            
            if proyecto_id not in totales_por_proyecto:
                totales_por_proyecto[proyecto_id] = {
                    "proyecto_id": proyecto_id,
                    "montoTotal": 0,
                    "cantidadRegistros": 0
                }
            
            totales_por_proyecto[proyecto_id]["montoTotal"] += monto
            totales_por_proyecto[proyecto_id]["cantidadRegistros"] += 1
        
        # Convertir a lista
        totales = list(totales_por_proyecto.values())
        
        return jsonify({
            "success": True,
            "totales": totales
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener totales: {e}")
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
