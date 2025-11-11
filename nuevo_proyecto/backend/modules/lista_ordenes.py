# backend/modules/lista_ordenes.py

from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required
from collections import defaultdict

bp = Blueprint("lista_ordenes_compra", __name__)


@bp.route("/", methods=["GET"])
@token_required
def get_lista_ordenes(current_user):
    """
    Obtiene lista de las últimas 500 órdenes de compra.
    Query param opcional: buscar=<texto> para buscar en órdenes antiguas
    """
    supabase = current_app.config['SUPABASE']
    buscar = request.args.get('buscar', '').strip()
    
    try:
        current_app.logger.info(f"📋 Iniciando carga de órdenes (buscar='{buscar}')...")
        
        # PASO 1: Obtener números de órdenes
        if buscar:
            # Si hay búsqueda, traer hasta 100 resultados filtrados
            current_app.logger.info(f"🔍 Búsqueda activa: {buscar}")
            ocs_query = supabase.table("orden_de_compra").select("orden_compra")
            
            # Buscar por número de OC
            if buscar.isdigit():
                ocs_query = ocs_query.eq("orden_compra", int(buscar))
            else:
                # Buscar en texto (proveedor o proyecto) - traer más registros
                ocs_query = ocs_query.order("orden_compra", desc=True).limit(2000)
            
            ultimas_ocs_res = ocs_query.execute()
        else:
            # Sin búsqueda: traer últimas 500
            ultimas_ocs_res = supabase.table("orden_de_compra").select(
                "orden_compra"
            ).order("orden_compra", desc=True).limit(1000).execute()  # Traer 1000 líneas para cubrir ~500 OCs
        
        if not ultimas_ocs_res.data:
            return jsonify({"success": True, "data": []})
        
        # Obtener números únicos y limitar a 500
        numeros_oc = sorted(list(set([oc['orden_compra'] for oc in ultimas_ocs_res.data])), reverse=True)[:500]
        
        current_app.logger.info(f"📦 Procesando {len(numeros_oc)} órdenes únicas")
        
        # PASO 2: Obtener TODAS las líneas de esas órdenes
        todas_lineas = []
        chunk_size = 100
        
        for i in range(0, len(numeros_oc), chunk_size):
            chunk = numeros_oc[i:i+chunk_size]
            lineas_res = supabase.table("orden_de_compra").select(
                "orden_compra, fecha, total, proveedor, proyecto, art_corr, cantidad"
            ).in_("orden_compra", chunk).execute()
            
            if lineas_res.data:
                todas_lineas.extend(lineas_res.data)
        
        current_app.logger.info(f"📄 Total líneas: {len(todas_lineas)}")
        
        # PASO 3: Obtener mapas de proveedores y proyectos
        proveedores_res = supabase.table("proveedores").select("id, nombre").execute()
        proveedores_map = {str(p['id']): p['nombre'] for p in (proveedores_res.data or [])}
        
        proyectos_res = supabase.table("proyectos").select("id, proyecto").execute()
        proyectos_map = {str(p['id']): p['proyecto'] for p in (proyectos_res.data or [])}
        
        # PASO 4: Obtener TODOS los ingresos con paginación
        current_app.logger.info("📥 Obteniendo ingresos con paginación...")
        todos_ingresos = []
        page_size = 1000
        offset = 0
        
        while True:
            batch = supabase.table("ingresos").select(
                "orden_compra, art_corr, recepcion"
            ).in_("orden_compra", numeros_oc).range(offset, offset + page_size - 1).execute()
            
            if not batch.data:
                break
            
            todos_ingresos.extend(batch.data)
            
            if len(batch.data) < page_size:
                break
            
            offset += page_size
        
        current_app.logger.info(f"📊 Total ingresos obtenidos: {len(todos_ingresos)}")
        
        # Agrupar por (orden_compra, art_corr) - NORMALIZAR A STRING
        cantidades_recibidas = defaultdict(lambda: defaultdict(int))
        for ing in todos_ingresos:
            oc_num = ing['orden_compra']
            art_corr = str(ing['art_corr'])  # ✅ Convertir a string
            recepcion = int(ing['recepcion'] or 0)
            cantidades_recibidas[oc_num][art_corr] += recepcion
        
        # PASO 5: Agrupar y calcular
        ordenes_agrupadas = defaultdict(lambda: {'lineas': [], 'total': 0})
        
        for linea in todas_lineas:
            oc_num = linea['orden_compra']
            if 'fecha' not in ordenes_agrupadas[oc_num]:
                ordenes_agrupadas[oc_num].update({
                    'orden_compra': oc_num,
                    'fecha': linea['fecha'],
                    'proveedor': proveedores_map.get(str(linea.get('proveedor', '')), 'N/A'),
                    'proyecto': proyectos_map.get(str(linea.get('proyecto', '')), 'N/A')
                })
            
            ordenes_agrupadas[oc_num]['total'] += (linea['total'] or 0)
            ordenes_agrupadas[oc_num]['lineas'].append({
                'art_corr': str(linea['art_corr']),  # ✅ Convertir a string
                'cantidad': linea.get('cantidad', 0)
            })
        
        # PASO 6: Calcular estados
        listado_final = []
        for oc_num, data in ordenes_agrupadas.items():
            total_sol = sum(ln['cantidad'] or 0 for ln in data['lineas'])
            total_rec = sum(cantidades_recibidas[oc_num][ln['art_corr']] for ln in data['lineas'])
            
            if total_rec == 0:
                estado = 'Pendiente'
            elif total_rec >= total_sol:
                estado = 'Recibida'
            else:
                estado = 'Parcial'
            
            # Filtrar por búsqueda de texto si aplica
            if buscar and not buscar.isdigit():
                buscar_lower = buscar.lower()
                if not (buscar_lower in data['proveedor'].lower() or 
                        buscar_lower in data['proyecto'].lower()):
                    continue
            
            listado_final.append({
                'orden_compra': data['orden_compra'],
                'fecha': data['fecha'],
                'proveedor': data['proveedor'],
                'estado': estado,
                'proyecto': data['proyecto'],
                'total': data['total']
            })
        
        listado_final.sort(key=lambda x: x['orden_compra'], reverse=True)
        
        current_app.logger.info(f"✅ Retornando {len(listado_final)} órdenes")
        return jsonify({"success": True, "data": listado_final})
    
    except Exception as e:
        current_app.logger.error(f"❌ Error: {str(e)}")
        current_app.logger.exception(e)
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/<int:oc_numero>", methods=["GET"])
@token_required
def get_detalle_orden(current_user, oc_numero):
    """Obtiene el detalle completo de una OC"""
    supabase = current_app.config['SUPABASE']
    
    try:
        current_app.logger.info(f"📄 Detalle OC {oc_numero}...")
        
        detalle_res = supabase.table("orden_de_compra").select("*").eq(
            "orden_compra", oc_numero
        ).order("art_corr").execute()
        
        if not detalle_res.data:
            return jsonify({"success": False, "message": "Orden no encontrada"}), 404
        
        primera = detalle_res.data[0]
        
        # Obtener datos relacionados
        proveedor_data = {'nombre': 'N/A', 'rut': 'N/A'}
        if primera.get('proveedor'):
            prov = supabase.table("proveedores").select("nombre, rut").eq("id", primera['proveedor']).limit(1).execute()
            if prov.data:
                proveedor_data = prov.data[0]
        
        proyecto_nombre = 'N/A'
        if primera.get('proyecto'):
            proy = supabase.table("proyectos").select("proyecto").eq("id", primera['proyecto']).limit(1).execute()
            if proy.data:
                proyecto_nombre = proy.data[0]['proyecto']
        
        solicitante_nombre = 'N/A'
        if primera.get('solicita'):
            trab = supabase.table("trabajadores").select("nombre").eq("id", primera['solicita']).limit(1).execute()
            if trab.data:
                solicitante_nombre = trab.data[0]['nombre']
        
        # Ingresos (usando campo 'recepcion' con paginación)
        current_app.logger.info(f"📥 Obteniendo ingresos para OC {oc_numero}...")
        todos_ingresos = []
        page_size = 1000
        offset = 0
        
        while True:
            batch = supabase.table("ingresos").select(
                "art_corr, recepcion"
            ).eq("orden_compra", oc_numero).range(offset, offset + page_size - 1).execute()
            
            if not batch.data:
                break
            
            todos_ingresos.extend(batch.data)
            
            if len(batch.data) < page_size:
                break
            
            offset += page_size
        
        current_app.logger.info(f"📊 Total ingresos: {len(todos_ingresos)}")
        
        cantidades_recibidas = defaultdict(int)
        for ing in todos_ingresos:
            cantidades_recibidas[str(ing['art_corr'])] += int(ing['recepcion'] or 0)  # ✅ Convertir a string
        
        # Construir respuesta
        orden_data = {
            "orden_compra": primera['orden_compra'],
            "fecha": primera['fecha'],
            "proveedor_nombre": proveedor_data['nombre'],
            "proveedor_rut": proveedor_data['rut'],
            "proyecto_nombre": proyecto_nombre,
            "solicitante_nombre": solicitante_nombre,
            "tipo_entrega": primera.get('tipo_de_entrega'),
            "plazo_pago": primera.get('condicion_de_pago'),
            "sin_iva": primera.get('fac_sin_iva') == 1,
            "lineas": [],
            "total_oc": 0
        }
        
        total_sol = 0
        total_rec = 0
        
        for linea in detalle_res.data:
            cant_sol = linea.get('cantidad') or 0
            cant_rec = cantidades_recibidas[str(linea['art_corr'])]  # ✅ Convertir a string
            
            total_sol += cant_sol
            total_rec += cant_rec
            
            estado_linea = "Recibida" if cant_rec >= cant_sol else ("Parcial" if cant_rec > 0 else "Pendiente")
            
            orden_data['lineas'].append({
                "art_corr": linea['art_corr'],
                "codigo": linea.get('codigo'),
                "descripcion": linea.get('descripcion'),
                "cantidad_solicitada": cant_sol,
                "cantidad_recibida": cant_rec,
                "precio_unitario": linea.get('precio_unitario'),
                "total_linea": linea.get('total'),
                "estado": estado_linea
            })
            
            orden_data['total_oc'] += (linea.get('total') or 0)
        
        orden_data['estado_general'] = 'Pendiente' if total_rec == 0 else ('Recibida' if total_rec >= total_sol else 'Parcial')
        
        current_app.logger.info(f"✅ Detalle OK")
        return jsonify({"success": True, "data": orden_data})
    
    except Exception as e:
        current_app.logger.error(f"❌ Error: {str(e)}")
        current_app.logger.exception(e)
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500