"""
API REST para Estado de Presupuesto
Visualización comparativa: Presupuesto vs Gastos Reales
"""
from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required
from datetime import datetime

bp = Blueprint("estado_presupuesto", __name__)


@bp.route("/", methods=["GET"])
@token_required
def get_estado_presupuesto(current_user):
    """
    Obtiene el estado de presupuesto: matriz de proyectos x items x meses
    Compara presupuesto vs gastos reales
    """
    supabase = current_app.config.get('SUPABASE')

    if not supabase:
        current_app.logger.error('Supabase client no configurado en current_app.config["SUPABASE"]')
        return jsonify({"success": False, "message": "Error de configuración del servidor"}), 500

    try:
        # Obtener proyectos
        res_proy = supabase.table("proyectos").select("id, proyecto").order("proyecto").execute()
        proyectos = res_proy.data if res_proy and hasattr(res_proy, 'data') else []

        
        # Obtener items presupuestarios
        # En la base actual la tabla se llama 'item' y la columna con el nombre es 'tipo'
        res_items = supabase.table("item").select("id, tipo").order("tipo").execute()
        raw_items = res_items.data if res_items and hasattr(res_items, 'data') else []
        # Normalizar al formato esperado por el frontend: { id, item }
        items = [{
            'id': it.get('id'),
            'item': it.get('tipo')
        } for it in raw_items]
        
        # Obtener presupuestos asignados
        res_pres = supabase.table("presupuesto_mensual").select("proyecto_id, item_id, mes, monto").execute()
        presupuestos = res_pres.data if res_pres and hasattr(res_pres, 'data') else []
        
        # Obtener órdenes de pago (gastos reales)
        res_ops = supabase.table("orden_de_pago").select("proyecto, item, mes, costo_final_con_iva, fecha_factura").not_.is_("fecha_factura", "null").execute()
        ordenes_pago = res_ops.data if res_ops and hasattr(res_ops, 'data') else []
        
        # Obtener gastos directos
        res_gd = supabase.table("gastos_directos").select("proyecto_id, item_id, mes, monto, fecha").execute()
        gastos_directos = res_gd.data if res_gd and hasattr(res_gd, 'data') else []

        # Loguear tamaños de conjuntos para diagnósticos y errores de consulta
        try:
            current_app.logger.debug(
                "estado_presupuesto: "
                f"proyectos={len(proyectos)}, "
                f"items={len(items)}, "
                f"presupuestos={len(presupuestos)}, "
                f"ordenes_pago={len(ordenes_pago)}, "
                f"gastos_directos={len(gastos_directos)}"
            )
        except Exception:
            # Si alguno no es iterable/loggable, loguear representación cruda
            current_app.logger.debug(
                "estado_presupuesto: respuesta cruda -> "
                f"res_proy={getattr(res_proy, 'error', getattr(res_proy, 'data', str(res_proy)))}, "
                f"res_items={getattr(res_items, 'error', getattr(res_items, 'data', str(res_items)))}, "
                f"res_pres={getattr(res_pres, 'error', getattr(res_pres, 'data', str(res_pres)))}, "
                f"res_ops={getattr(res_ops, 'error', getattr(res_ops, 'data', str(res_ops)))}, "
                f"res_gd={getattr(res_gd, 'error', getattr(res_gd, 'data', str(res_gd)))}"
            )
        
        # Construir matriz de datos
        matriz = {}
        
        # Inicializar matriz
        for proyecto in proyectos:
            proyecto_id = proyecto['id']
            matriz[proyecto_id] = {
                'nombre': proyecto['proyecto'],
                'items': {}
            }
            for item in items:
                item_id = item['id']
                matriz[proyecto_id]['items'][item_id] = {
                    'nombre': item['item'],
                    'meses': {},
                    'total_presupuesto': 0,
                    'total_real': 0
                }
        
        # Procesar presupuestos
        for p in presupuestos:
            proyecto_id = p.get('proyecto_id')
            item_id = p.get('item_id')
            mes = p.get('mes')
            monto = float(p.get('monto', 0) or 0)
            
            if proyecto_id in matriz and item_id in matriz[proyecto_id]['items']:
                if mes not in matriz[proyecto_id]['items'][item_id]['meses']:
                    matriz[proyecto_id]['items'][item_id]['meses'][mes] = {
                        'presupuesto': 0,
                        'real': 0,
                        'diferencia': 0
                    }
                matriz[proyecto_id]['items'][item_id]['meses'][mes]['presupuesto'] = monto
                matriz[proyecto_id]['items'][item_id]['total_presupuesto'] += monto
        
        # Procesar órdenes de pago (gastos reales)
        for op in ordenes_pago:
            proyecto_id = op.get('proyecto')
            item_id = op.get('item')
            mes = op.get('mes')
            monto = float(op.get('costo_final_con_iva', 0) or 0)
            
            if proyecto_id in matriz and item_id in matriz[proyecto_id]['items']:
                if mes not in matriz[proyecto_id]['items'][item_id]['meses']:
                    matriz[proyecto_id]['items'][item_id]['meses'][mes] = {
                        'presupuesto': 0,
                        'real': 0,
                        'diferencia': 0
                    }
                matriz[proyecto_id]['items'][item_id]['meses'][mes]['real'] += monto
                matriz[proyecto_id]['items'][item_id]['total_real'] += monto
        
        # Procesar gastos directos
        for gd in gastos_directos:
            proyecto_id = gd.get('proyecto_id')
            item_id = gd.get('item_id')
            mes = gd.get('mes')
            monto = float(gd.get('monto', 0) or 0)
            
            if proyecto_id in matriz and item_id in matriz[proyecto_id]['items']:
                # Convertir mes español a número
                mes_num = convertir_mes_a_numero(mes)
                if mes_num:
                    if mes_num not in matriz[proyecto_id]['items'][item_id]['meses']:
                        matriz[proyecto_id]['items'][item_id]['meses'][mes_num] = {
                            'presupuesto': 0,
                            'real': 0,
                            'diferencia': 0
                        }
                    matriz[proyecto_id]['items'][item_id]['meses'][mes_num]['real'] += monto
                    matriz[proyecto_id]['items'][item_id]['total_real'] += monto
        
        # Calcular diferencias
        for proyecto_id in matriz:
            for item_id in matriz[proyecto_id]['items']:
                for mes in matriz[proyecto_id]['items'][item_id]['meses']:
                    datos = matriz[proyecto_id]['items'][item_id]['meses'][mes]
                    datos['diferencia'] = datos['presupuesto'] - datos['real']
        
        # Calcular totales generales
        totales = {
            'presupuesto_total': 0,
            'real_total': 0,
            'diferencia_total': 0
        }
        
        for proyecto_id in matriz:
            for item_id in matriz[proyecto_id]['items']:
                totales['presupuesto_total'] += matriz[proyecto_id]['items'][item_id]['total_presupuesto']
                totales['real_total'] += matriz[proyecto_id]['items'][item_id]['total_real']
        
        totales['diferencia_total'] = totales['presupuesto_total'] - totales['real_total']
        
        return jsonify({
            "success": True,
            "data": {
                "matriz": matriz,
                "proyectos": proyectos,
                "items": items,
                "totales": totales
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener estado de presupuesto: {e}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500


@bp.route("/detalle", methods=["GET"])
@token_required
def get_detalle_gasto(current_user):
    """
    Obtiene el detalle de gastos para un proyecto/item/mes específico
    """
    supabase = current_app.config['SUPABASE']
    
    proyecto_id = request.args.get('proyecto')
    item_id = request.args.get('item')
    mes = request.args.get('mes')
    
    if not all([proyecto_id, item_id, mes]):
        return jsonify({
            "success": False,
            "message": "Faltan parámetros: proyecto, item, mes"
        }), 400
    
    try:
        # Obtener nombre del proyecto
        proyecto = (
            supabase.table("proyectos")
            .select("proyecto")
            .eq("id", proyecto_id)
            .execute()
        )
        proyecto_data = proyecto.data if proyecto and hasattr(proyecto, 'data') else []
        nombre_proyecto = proyecto_data[0]['proyecto'] if proyecto_data else f"Proyecto {proyecto_id}"
        
        # Obtener nombre del item
        item = (
            # La tabla de items se llama 'item' y el campo con el nombre es 'tipo'
            supabase.table("item")
            .select("tipo")
            .eq("id", item_id)
            .execute()
        )
        item_data = item.data if item and hasattr(item, 'data') else []
        nombre_item = item_data[0]['tipo'] if item_data else f"Item {item_id}"
        
        # Obtener órdenes de pago
        ordenes = (
            supabase.table("orden_de_pago")
            .select("id, orden_numero, orden_compra, proveedor_nombre, material_nombre, costo_final_con_iva, fecha_factura")
            .eq("proyecto", proyecto_id)
            .eq("item", item_id)
            .eq("mes", mes)
            .not_.is_("fecha_factura", "null")
            .execute()
            .data or []
        )
        
        # Obtener gastos directos
        mes_nombre = convertir_numero_a_mes(int(mes))
        gastos = (
            supabase.table("gastos_directos")
            .select("id, descripcion, monto, fecha")
            .eq("proyecto_id", proyecto_id)
            .eq("item_id", item_id)
            .eq("mes", mes_nombre)
            .execute()
            .data or []
        )
        
        # Calcular totales
        total_ordenes = sum(float(o.get('costo_final_con_iva', 0) or 0) for o in ordenes)
        total_gastos = sum(float(g.get('monto', 0) or 0) for g in gastos)
        total_general = total_ordenes + total_gastos
        
        return jsonify({
            "success": True,
            "data": {
                "proyecto": nombre_proyecto,
                "item": nombre_item,
                "mes": mes,
                "ordenes": ordenes,
                "gastos": gastos,
                "totales": {
                    "ordenes": total_ordenes,
                    "gastos": total_gastos,
                    "general": total_general
                }
            }
        })
        
    except Exception as e:
        current_app.logger.exception(f"Error al obtener detalle de gasto for proyecto={proyecto_id}, item={item_id}, mes={mes}: {e}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500


@bp.route("/update", methods=["POST"])
@token_required
def update_presupuesto(current_user):
    """
    Actualiza el monto de presupuesto para un proyecto/item/mes
    """
    supabase = current_app.config['SUPABASE']
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "message": "No se recibieron datos"}), 400
    
    proyecto_id = data.get('proyecto_id')
    item_id = data.get('item_id')
    mes = data.get('mes')
    monto = data.get('monto')
    
    if not all([proyecto_id, item_id, mes, monto is not None]):
        return jsonify({
            "success": False,
            "message": "Faltan parámetros requeridos"
        }), 400
    
    try:
        # Convertir a tipos correctos
        proyecto_id = int(proyecto_id)
        item_id = int(item_id)
        mes = int(mes)
        monto = float(monto)
        
        # Verificar si ya existe un registro
        existing = (
            supabase.table("presupuesto_mensual")
            .select("id")
            .eq("proyecto_id", proyecto_id)
            .eq("item_id", item_id)
            .eq("mes", mes)
            .execute()
            .data
        )
        
        if existing:
            # Actualizar
            result = (
                supabase.table("presupuesto_mensual")
                .update({"monto": monto})
                .eq("id", existing[0]['id'])
                .execute()
            )
        else:
            # Insertar
            result = (
                supabase.table("presupuesto_mensual")
                .insert({
                    "proyecto_id": proyecto_id,
                    "item_id": item_id,
                    "mes": mes,
                    "monto": monto
                })
                .execute()
            )
        
        return jsonify({
            "success": True,
            "message": "Presupuesto actualizado correctamente"
        })
        
    except Exception as e:
        current_app.logger.exception(f"Error al actualizar presupuesto for proyecto={proyecto_id}, item={item_id}, mes={mes}: {e}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500


# Funciones auxiliares
def convertir_mes_a_numero(mes_nombre):
    """Convierte nombre de mes en español a número (1-12)"""
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    return meses.get(mes_nombre.lower() if mes_nombre else '')


def convertir_numero_a_mes(mes_num):
    """Convierte número de mes (1-12) a nombre en español"""
    meses = [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]
    return meses[mes_num - 1] if 1 <= mes_num <= 12 else ''