import re
from datetime import date
from collections import defaultdict
from flask import Blueprint, request, jsonify, current_app

# ========= Importaciones de Utilidades del Nuevo Proyecto =========
# Decorador para proteger rutas, asegurando que solo usuarios logueados accedan.
from backend.utils.decorators import token_required
# Decorador para cachear respuestas de la API en Redis y mejorar el rendimiento.
from backend.utils.cache import cache_result

bp = Blueprint("ordenes", __name__)

# ========= Funciones Auxiliares (Adaptadas del sistema anterior) =========

def parse_monto(x):
    """
    Convierte un string de moneda (ej: "$1.234.567,89") a un float.
    Lógica extraída directamente del 'ordenes.py' anterior.
    """
    if not x:
        return 0.0
    # Lógica de limpieza y conversión
    limpio = re.sub(r'[^\d,\.]', '', str(x))
    partes = limpio.split(',')
    if len(partes) > 1:
        dec = partes[-1]
        ent = ''.join(partes[:-1])
        limpio2 = ent.replace('.', '') + '.' + dec
    else:
        limpio2 = partes[0].replace('.', '')
    try:
        return float(limpio2)
    except (ValueError, TypeError):
        return 0.0

# ================================================================
# ENDPOINT PRINCIPAL DE ÓRDENES (CRUD)
# ================================================================

@bp.route("/", methods=["POST"])
@token_required
def create_orden(current_user):
    """
    Endpoint para crear una nueva Orden de Compra.
    Adapta la lógica POST de la función 'new_orden' del sistema anterior.
    """
    data = request.get_json()
    
    # Extraer header y validar datos requeridos
    header = data.get('header', {}) if data else {}
    lineas = data.get('lineas', []) if data else []
    
    # Log para debugging
    current_app.logger.info(f"📦 Creando OC - Proveedor: {header.get('proveedor_id')}, Líneas: {len(lineas)}")
    
    if not header.get('proveedor_id') or not lineas:
        return jsonify({"success": False, "message": "Faltan datos requeridos (proveedor, líneas)"}), 400

    supabase = current_app.config['SUPABASE']

    try:
        # --- 1. Calcular próximo N° de OC y art_corr (lógica idéntica al sistema anterior) ---
        last_oc = supabase.table("orden_de_compra").select("orden_compra").order("orden_compra", desc=True).limit(1).execute().data
        next_oc_num = (int(last_oc[0]["orden_compra"]) if last_oc else 0) + 1

        last_corr = supabase.table("orden_de_compra").select("art_corr").order("art_corr", desc=True).limit(1).execute().data
        next_corr_num = (int(last_corr[0]["art_corr"]) if last_corr else 0) + 1

        # --- 2. Preparar las filas para la inserción masiva ---
        hoy = date.today()
        rows_to_insert = []
        
        # Log para debugging
        current_app.logger.info(f"📝 Procesando {len(lineas)} líneas")
        
        # Obtener todos los códigos de materiales para hacer una consulta en batch
        codigos = [linea.get('codigo', '') for linea in lineas if linea.get('codigo')]
        items_map = {}
        
        if codigos:
            # Consultar items de materiales
            materiales_res = supabase.table("materiales").select("cod, item").in_("cod", codigos).execute()
            if materiales_res.data:
                items_map = {mat['cod']: mat.get('item') for mat in materiales_res.data}
                current_app.logger.info(f"📦 Items encontrados: {items_map}")
        
        for i, linea in enumerate(lineas):
            current_app.logger.info(f"  Línea {i+1}: {linea}")
            
            if not linea.get('cantidad') or float(linea['cantidad']) <= 0:
                current_app.logger.warning(f"  ⚠️ Línea {i+1} omitida: cantidad inválida")
                continue # Omitir líneas sin cantidad

            codigo = linea.get('codigo', '')
            item_value = items_map.get(codigo) if codigo else None
            
            row_data = {
                "orden_compra": next_oc_num,
                "fecha": hoy.isoformat(),
                "mes": hoy.month,
                "semana": hoy.isocalendar()[1],
                "proveedor": header.get('proveedor_id'),
                "tipo_de_entrega": header.get('tipo_entrega'),
                "condicion_de_pago": header.get('plazo_pago'),
                "fac_sin_iva": 1 if header.get('sin_iva') else 0, # 1 para sin IVA, 0 para con IVA
                "proyecto": header.get('proyecto_id'),
                "solicita": header.get('solicitado_por'),
                "art_corr": next_corr_num + i,
                "codigo": codigo,
                "descripcion": linea.get('descripcion'),
                "cantidad": int(linea['cantidad']),
                "precio_unitario": parse_monto(linea.get('neto')),
                "total": parse_monto(linea.get('total')),
                "item": item_value,  # ← AGREGADO: obtener item desde materiales
                "estado_pago": "0" # Estado inicial por defecto
            }
            
            current_app.logger.info(f"  ✓ Fila preparada (item: {item_value}): {row_data}")
            rows_to_insert.append(row_data)

        current_app.logger.info(f"📊 Total de filas a insertar: {len(rows_to_insert)}")
        
        if not rows_to_insert:
            return jsonify({"success": False, "message": "No se encontraron líneas válidas para guardar."}), 400

        # --- 3. Insertar en Supabase ---
        current_app.logger.info(f"💾 Insertando {len(rows_to_insert)} filas en la base de datos...")
        res = supabase.table("orden_de_compra").insert(rows_to_insert).execute()
        
        current_app.logger.info(f"📥 Respuesta de Supabase - Data: {res.data}, Count: {res.count if hasattr(res, 'count') else 'N/A'}")

        # En Supabase v2, el error se encuentra en el objeto `error`
        if res.data:
             return jsonify({"success": True, "message": f"Orden de Compra {next_oc_num} creada exitosamente con {len(res.data)} líneas.", "orden_compra": next_oc_num})
        else:
            # Manejar el caso de que no haya datos y tampoco error explícito
            current_app.logger.error(f"❌ No se obtuvieron datos en la respuesta de Supabase")
            return jsonify({"success": False, "message": "Error desconocido al guardar la orden."}), 500

    except Exception as e:
        # Log del error es buena práctica
        current_app.logger.error(f"Error al crear OC: {str(e)}")
        return jsonify({"success": False, "message": f"Error interno del servidor: {str(e)}"}), 500


@bp.route("/", methods=["GET"])
@token_required
# @cache_result(ttl_seconds=60) # Cache comentado: causa error de serialización con User
def get_listado_ordenes(current_user):
    """
    Devuelve un listado resumido de todas las órdenes de compra.
    Adapta la lógica de 'api_get_listado_ordenes' del sistema anterior.
    """
    supabase = current_app.config['SUPABASE']
    try:
        # --- 1. Obtener todas las líneas con JOINs (más eficiente) ---
        ordenes_res = supabase.table("orden_de_compra").select(
            "orden_compra, fecha, total, proveedores(nombre), proyectos(proyecto)"
        ).order("fecha", desc=True).execute()

        if not ordenes_res.data:
            return jsonify({"success": True, "data": []})

        # --- 2. Obtener OCs con ingresos para determinar estado ---
        ingresos_res = supabase.table("ingresos").select("orden_compra").execute()
        ocs_recibidas = {ingreso['orden_compra'] for ingreso in (ingresos_res.data or [])}

        # --- 3. Agrupar en Python (lógica idéntica a la anterior) ---
        ordenes_agrupadas = defaultdict(lambda: {'total': 0, 'lineas': 0})
        for linea in ordenes_res.data:
            oc_num = linea['orden_compra']
            if 'fecha' not in ordenes_agrupadas[oc_num]: # Llenar datos solo en la primera aparición
                ordenes_agrupadas[oc_num]['orden_compra'] = oc_num
                ordenes_agrupadas[oc_num]['fecha'] = linea['fecha']
                ordenes_agrupadas[oc_num]['proveedor'] = linea['proveedores']['nombre'] if linea.get('proveedores') else 'N/A'
                ordenes_agrupadas[oc_num]['proyecto'] = linea['proyectos']['proyecto'] if linea.get('proyectos') else 'N/A'
            
            ordenes_agrupadas[oc_num]['total'] += (linea['total'] or 0)
            ordenes_agrupadas[oc_num]['lineas'] += 1

        # --- 4. Determinar estado y convertir a lista ---
        listado_final = []
        for oc_num, data in ordenes_agrupadas.items():
            data['estado'] = 'Recibida' if oc_num in ocs_recibidas else 'Pendiente'
            listado_final.append(data)
            
        listado_final = sorted(listado_final, key=lambda x: x['orden_compra'], reverse=True)

        return jsonify({"success": True, "data": listado_final})

    except Exception as e:
        current_app.logger.error(f"Error en listado de órdenes: {str(e)}")
        return jsonify({"success": False, "message": "Error al obtener las órdenes"}), 500


@bp.route("/<int:oc_numero>", methods=["GET"])
@token_required
# @cache_result(ttl_seconds=120) # Cache comentado: causa error de serialización con User
def get_detalle_orden(current_user, oc_numero):
    """
    Devuelve el detalle completo de una OC específica.
    Adapta la lógica de 'api_get_detalle_orden_compra'.
    """
    supabase = current_app.config['SUPABASE']
    try:
        # --- 1. Obtener todas las líneas de la OC con JOINs ---
        detalle_res = supabase.table("orden_de_compra").select(
            "*, proveedores(nombre, rut), proyectos(proyecto), trabajadores!orden_de_compra_solicita_fkey(nombre)"
        ).eq("orden_compra", oc_numero).order("art_corr").execute()

        if not detalle_res.data:
            return jsonify({"success": False, "message": "Orden de Compra no encontrada"}), 404

        # --- 2. Obtener cantidades recibidas desde 'ingresos' ---
        ingresos_res = supabase.table("ingresos").select("art_corr, cantidad_ingresada").eq("orden_compra", oc_numero).execute()
        cantidades_recibidas = defaultdict(int)
        for ingreso in (ingresos_res.data or []):
            cantidades_recibidas[ingreso['art_corr']] += (ingreso['cantidad_ingresada'] or 0)

        # --- 3. Procesar y construir la respuesta JSON ---
        primera_linea = detalle_res.data[0]
        orden_data = {
            "orden_compra": primera_linea['orden_compra'],
            "fecha": primera_linea['fecha'],
            "proveedor_nombre": primera_linea['proveedores']['nombre'] if primera_linea.get('proveedores') else 'N/A',
            "proveedor_rut": primera_linea['proveedores']['rut'] if primera_linea.get('proveedores') else 'N/A',
            "proyecto_nombre": primera_linea['proyectos']['proyecto'] if primera_linea.get('proyectos') else 'N/A',
            "solicitante_nombre": primera_linea['trabajadores']['nombre'] if primera_linea.get('trabajadores') else 'N/A',
            "tipo_entrega": primera_linea['tipo_de_entrega'],
            "plazo_pago": primera_linea['condicion_de_pago'],
            "sin_iva": primera_linea['fac_sin_iva'] == 1,
            "lineas": [],
            "total_oc": 0
        }

        total_solicitado = 0
        total_recibido = 0
        for linea in detalle_res.data:
            cantidad_solicitada = linea['cantidad'] or 0
            cantidad_recibida = cantidades_recibidas[linea['art_corr']]
            total_solicitado += cantidad_solicitada
            total_recibido += cantidad_recibida
            
            estado_linea = "Recibida" if cantidad_recibida >= cantidad_solicitada else \
                           "Parcial" if cantidad_recibida > 0 else "Pendiente"

            orden_data['lineas'].append({
                "art_corr": linea['art_corr'],
                "codigo": linea['codigo'],
                "descripcion": linea['descripcion'],
                "cantidad_solicitada": cantidad_solicitada,
                "cantidad_recibida": cantidad_recibida,
                "precio_unitario": linea['precio_unitario'],
                "total_linea": linea['total'],
                "estado": estado_linea
            })
            orden_data['total_oc'] += (linea['total'] or 0)
        
        # Calcular estado general
        if total_recibido == 0:
            orden_data['estado_general'] = 'Pendiente'
        elif total_recibido >= total_solicitado:
            orden_data['estado_general'] = 'Recibida Completa'
        else:
            orden_data['estado_general'] = 'Recepción Parcial'

        return jsonify({"success": True, "data": orden_data})

    except Exception as e:
        current_app.logger.error(f"Error en detalle de OC {oc_numero}: {str(e)}")
        return jsonify({"success": False, "message": f"Error al obtener detalle de la OC"}), 500


# ================================================================
# ENDPOINTS AUXILIARES
# ================================================================

@bp.route("/helpers/next-number", methods=["GET"])
@token_required
def get_next_oc_number(current_user):
    """
    Obtiene el próximo número de orden de compra disponible.
    """
    supabase = current_app.config['SUPABASE']
    try:
        # Consultar la tabla con el nombre exacto de la columna
        last_oc = supabase.table("orden_de_compra").select("orden_compra").order("orden_compra", desc=True).limit(1).execute()
        
        # Log detallado para debugging
        current_app.logger.info(f"Last OC response: {last_oc}")
        
        if last_oc.data and len(last_oc.data) > 0:
            next_num = int(last_oc.data[0]["orden_compra"]) + 1
        else:
            next_num = 1
            
        return jsonify({"success": True, "next_number": next_num})
    except Exception as e:
        current_app.logger.error(f"Error al obtener próximo número OC: {str(e)}")
        return jsonify({"success": False, "message": str(e), "next_number": 1})


# ================================================================
# ENDPOINTS PARA AUTOCOMPLETADO (SELECTS DEL FRONTEND)
# ================================================================

@bp.route("/helpers/autocomplete/<string:resource>", methods=["GET"])
@token_required
# @cache_result(ttl_seconds=600) # Comentado: causa error de serialización con User
def get_autocomplete_data(current_user, resource):
    """
    Endpoint genérico para autocompletado.
    Recurso puede ser: 'proveedores', 'proyectos', 'trabajadores', 'materiales'.
    
    Parámetros:
    - term: Término de búsqueda (opcional)
    - limit: Número máximo de resultados (default: 20, se usa cuando no hay term)
    """
    term = request.args.get('term', '').strip()
    limit = request.args.get('limit', '20')
    
    try:
        limit = int(limit)
        if limit > 50:  # Máximo 50 resultados
            limit = 50
    except ValueError:
        limit = 20

    supabase = current_app.config['SUPABASE']
    
    # Mapeo para configurar la búsqueda por recurso
    config = {
        'proveedores': {
            'table': 'proveedores', 
            'search_field': 'nombre', 
            'value_field': 'id', 
            'label_field': 'nombre',
            'extra_fields': 'rut'  # Agregamos el RUT
        },
        'proyectos': {'table': 'proyectos', 'search_field': 'proyecto', 'value_field': 'id', 'label_field': 'proyecto', 'filter_active': True},
        'trabajadores': {'table': 'trabajadores', 'search_field': 'nombre', 'value_field': 'id', 'label_field': 'nombre'},
        'materiales': {'table': 'materiales', 'search_field': 'material', 'value_field': 'cod', 'label_field': 'material'}
    }

    if resource not in config:
        return jsonify({"success": False, "message": "Recurso no válido"}), 404

    res_config = config[resource]
    try:
        # Construir la query base - incluir campos extra si existen
        select_fields = f"{res_config['value_field']}, {res_config['label_field']}"
        if res_config.get('extra_fields'):
            select_fields += f", {res_config['extra_fields']}"
        
        query = supabase.table(res_config['table']).select(select_fields)
        
        # Si hay término de búsqueda, aplicar filtro ilike
        if term and len(term) >= 2:
            query = query.ilike(res_config['search_field'], f"%{term}%")
        
        # Aplicar filtros adicionales según el recurso
        if res_config.get('filter_active'):
            query = query.eq('activo', True)
        
        # Ordenar y limitar resultados
        query = query.order(res_config['label_field']).limit(limit)
            
        response = query.execute()

        if not response.data:
            return jsonify({"results": []})

        # Formatear para react-select: { value, label, ...extras }
        results = []
        for item in response.data:
            result_item = {
                "value": item[res_config['value_field']],
                "label": item[res_config['label_field']]
            }
            
            # Agregar campos extra si existen (ej: rut para proveedores)
            if res_config.get('extra_fields'):
                extra_field = res_config['extra_fields']
                if extra_field in item:
                    result_item[extra_field] = item[extra_field]
            
            results.append(result_item)

        return jsonify({"results": results})

    except Exception as e:
        current_app.logger.error(f"Error en autocompletado para '{resource}': {str(e)}")
        return jsonify({"success": False, "message": "Error en la búsqueda"}), 500


@bp.route("/helpers/material/<string:codigo>/ultimo-precio", methods=["GET"])
@token_required
def get_ultimo_precio_material(current_user, codigo):
    """
    Obtiene el último precio registrado para un material específico.
    Busca en orden_de_compra el precio_unitario más reciente.
    """
    supabase = current_app.config['SUPABASE']
    
    try:
        # Buscar el último precio unitario registrado para este material
        result = supabase.table("orden_de_compra") \
            .select("precio_unitario, fecha") \
            .eq("codigo", codigo) \
            .order("fecha", desc=True) \
            .limit(1) \
            .execute()
        
        if result.data and len(result.data) > 0:
            ultimo_precio = result.data[0].get('precio_unitario', 0)
            fecha = result.data[0].get('fecha')
            
            return jsonify({
                "success": True,
                "precio": float(ultimo_precio) if ultimo_precio else 0,
                "fecha": fecha
            })
        else:
            # No hay precios previos
            return jsonify({
                "success": True,
                "precio": 0,
                "fecha": None
            })
    except Exception as e:
        current_app.logger.error(f"Error al obtener último precio de material {codigo}: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e),
            "precio": 0
        }), 500
