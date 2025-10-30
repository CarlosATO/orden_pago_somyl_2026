"""
API REST para Estado de Presupuesto
Visualización comparativa: Presupuesto vs Gastos Reales
VERSIÓN BASADA EN SISTEMA ANTIGUO QUE FUNCIONA
"""
from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required
from datetime import datetime
import logging
import os
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

bp = Blueprint("estado_presupuesto", __name__)
logger = logging.getLogger(__name__)


def get_produccion_actual_nhost(supabase_proyecto_id):
    """
    Obtiene la producción actual desde Nhost para un proyecto específico
    
    Args:
        supabase_proyecto_id: ID del proyecto en Supabase
        
    Returns:
        float: Total de producción actual, o 0 si no hay datos
    """
    try:
        nhost_url = os.environ.get("NHOST_GRAPHQL_URL")
        nhost_secret = os.environ.get("NHOST_ADMIN_SECRET")
        
        if not nhost_url or not nhost_secret:
            logger.warning("Credenciales de Nhost no configuradas")
            return 0
        
        # Configurar cliente GraphQL
        transport = RequestsHTTPTransport(
            url=nhost_url,
            headers={'x-hasura-admin-secret': nhost_secret},
            verify=True,
            retries=2,
        )
        
        client = Client(transport=transport, fetch_schema_from_transport=False)
        
        # PASO 1: Buscar proyecto en Nhost por supabase_proyecto_id
        query_proyecto = gql("""
        query GetProyecto($supabase_id: Int!) {
            proyectos(where: {supabase_proyecto_id: {_eq: $supabase_id}}) {
                id
            }
        }
        """)
        
        result_proyecto = client.execute(query_proyecto, variable_values={"supabase_id": supabase_proyecto_id})
        
        if not result_proyecto['proyectos']:
            logger.info(f"Proyecto {supabase_proyecto_id} no está habilitado en sistema de producción")
            return 0
        
        id_local = result_proyecto['proyectos'][0]['id']
        
        # PASO 2: Obtener datos operativos y sumar venta_total
        query_datos = gql("""
        query GetDatosOperativos($id_proyecto: Int!) {
            datos_operativos(where: {id_proyecto: {_eq: $id_proyecto}}) {
                venta_total
            }
        }
        """)
        
        result_datos = client.execute(query_datos, variable_values={"id_proyecto": id_local})
        
        # Sumar venta_total
        total = sum(float(dato.get('venta_total', 0) or 0) for dato in result_datos['datos_operativos'])
        
        logger.info(f"✅ Producción Nhost para proyecto {supabase_proyecto_id}: ${total:,.0f}")
        return total
        
    except Exception as e:
        logger.error(f"Error obteniendo producción desde Nhost: {type(e).__name__}: {str(e)}")
        return 0


@bp.route("/", methods=["GET"])
@token_required
def get_estado_presupuesto(current_user):
    """
    Obtiene el estado de presupuesto: matriz de proyectos x items x meses
    Compara presupuesto vs gastos reales
    Acepta parámetro ?proyecto_id=X para filtrar por proyecto específico
    """
    supabase = current_app.config.get('SUPABASE')

    if not supabase:
        logger.error('Supabase client no configurado')
        return jsonify({"success": False, "message": "Error de configuración del servidor"}), 500

    try:
        logger.info("=== Iniciando consulta de estado de presupuesto ===")
        
        # Obtener filtro de proyecto desde query string
        proyecto_filter = request.args.get('proyecto_id', '')
        logger.info(f"📌 Filtro de proyecto recibido: '{proyecto_filter}'")
        
        # 1. Obtener proyectos - SOLO ACTIVOS Y NO FINALIZADOS
        res_proy = supabase.table("proyectos").select("id, proyecto, activo, observacion, venta, produccion").order("proyecto").execute()
        all_proyectos = res_proy.data if res_proy and hasattr(res_proy, 'data') else []
        
        # Filtrar: solo activos y no finalizados
        proyectos = []
        proyecto_ids = []
        for p in all_proyectos:
            # Debe ser activo
            if not p.get('activo', False):
                continue
            
            # Verificar observación
            observacion = p.get('observacion')
            if observacion:
                obs_str = str(observacion).strip().lower()
                if obs_str == 'finalizado':
                    continue
            
            # Aplicar filtro de proyecto específico si se proporciona
            if proyecto_filter and proyecto_filter != 'todos':
                try:
                    if p['id'] != int(proyecto_filter):
                        continue
                except:
                    pass
            
            proyectos.append(p)
            proyecto_ids.append(p['id'])
        
        logger.info(f"✅ Proyectos: {len(proyectos)} activos de {len(all_proyectos)} totales")
        logger.info(f"📋 IDs de proyectos: {proyecto_ids}")
        
        # 2. Obtener items
        try:
            res_items = supabase.table("item").select("id, tipo").order("tipo").execute()
            raw_items = res_items.data if res_items and hasattr(res_items, 'data') else []
            logger.info(f"✅ Items obtenidos: {len(raw_items)}")
        except:
            res_items = supabase.table("items").select("id, tipo").order("tipo").execute()
            raw_items = res_items.data if res_items and hasattr(res_items, 'data') else []
            logger.info(f"✅ Items obtenidos (tabla items): {len(raw_items)}")
        
        # Crear mapeos de items
        items = []
        id_to_tipo = {}
        tipo_to_id = {}
        
        for it in raw_items:
            item_id = it.get('id')
            tipo_raw = it.get('tipo', '')
            
            # Normalizar tipo (eliminar plural)
            tipo = str(tipo_raw).upper().strip()
            if tipo.endswith('S') and len(tipo) > 3:
                tipo = tipo[:-1]
            
            items.append({'id': item_id, 'item': tipo})
            id_to_tipo[item_id] = tipo
            tipo_to_id[tipo] = item_id
        
        logger.info(f"✅ Items normalizados: {len(items)}")
        
        # 3. Obtener presupuestos - FILTRADOS POR PROYECTO
        presupuestos = []
        page_size = 1000
        page = 0
        
        while True:
            query = (
                supabase.table("presupuesto")
                .select("proyecto_id, item, mes_numero, monto, fecha")
                .in_("proyecto_id", proyecto_ids)
                .range(page * page_size, (page + 1) * page_size - 1)
            )
            chunk = query.execute().data or []
            presupuestos.extend(chunk)
            
            if len(chunk) < page_size:
                break
            page += 1
        
        logger.info(f"✅ Presupuestos: {len(presupuestos)}")
        
        # 4. Obtener órdenes de pago - FILTRADAS POR PROYECTO (CLAVE!)
        ordenes_pago = []
        page = 0
        
        logger.info(f"🔍 Consultando órdenes de pago para proyectos: {proyecto_ids}")
        
        while True:
            query = (
                supabase.table("orden_de_pago")
                .select("proyecto, item, mes, costo_final_con_iva, fecha_factura")
                .in_("proyecto", proyecto_ids)  # 👈 FILTRO DIRECTO EN LA CONSULTA
                # REMOVIDO: .not_.is_("fecha_factura", "null")  # ❌ Esto elimina órdenes válidas
                .range(page * page_size, (page + 1) * page_size - 1)
            )
            chunk = query.execute().data or []
            ordenes_pago.extend(chunk)
            
            if len(chunk) < page_size:
                break
            page += 1
        
        logger.info(f"✅ Órdenes de pago: {len(ordenes_pago)}")
        
        # 5. Obtener gastos directos - FILTRADOS POR PROYECTO
        gastos_directos = []
        page = 0
        
        while True:
            query = (
                supabase.table("gastos_directos")
                .select("proyecto_id, item_id, mes, monto, fecha")
                .in_("proyecto_id", proyecto_ids)
                .range(page * page_size, (page + 1) * page_size - 1)
            )
            chunk = query.execute().data or []
            gastos_directos.extend(chunk)
            
            if len(chunk) < page_size:
                break
            page += 1
        
        logger.info(f"✅ Gastos directos: {len(gastos_directos)}")

        # 6. Inicializar matriz
        matriz = {}
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
                    'total_real': 0,
                    'diferencia': 0
                }
                
                # Inicializar 12 meses
                for mes in range(1, 13):
                    matriz[proyecto_id]['items'][item_id]['meses'][mes] = {
                        'presupuesto': 0,
                        'real': 0,
                        'diferencia': 0
                    }

        # 7. Procesar presupuestos
        for pres in presupuestos:
            proyecto_id = pres.get('proyecto_id')
            item_val = pres.get('item')
            mes = pres.get('mes_numero')
            monto = float(pres.get('monto', 0) or 0)
            
            if not all([proyecto_id, item_val, mes]):
                continue
            
            if proyecto_id not in matriz:
                continue
            
            # Normalizar item
            item_id = None
            if isinstance(item_val, int):
                item_id = item_val if item_val in id_to_tipo else None
            else:
                tipo = str(item_val).upper().strip()
                if tipo:
                    if tipo.endswith('S') and len(tipo) > 3:
                        tipo = tipo[:-1]
                    item_id = tipo_to_id.get(tipo)
            
            if item_id and item_id in matriz[proyecto_id]['items']:
                if mes in matriz[proyecto_id]['items'][item_id]['meses']:
                    matriz[proyecto_id]['items'][item_id]['meses'][mes]['presupuesto'] += monto
                    matriz[proyecto_id]['items'][item_id]['total_presupuesto'] += monto

        logger.info("✅ Presupuestos procesados")

        # 8. Procesar órdenes de pago
        contador_ops = 0
        ordenes_saltadas = 0
        razones_salto = {'sin_proyecto': 0, 'proyecto_invalido': 0, 'proyecto_no_en_matriz': 0, 
                        'sin_item': 0, 'item_no_normalizado': 0, 'item_no_en_matriz': 0,
                        'sin_mes': 0, 'mes_invalido': 0, 'mes_fuera_rango': 0}
        
        for op in ordenes_pago:
            # Ya vienen filtradas por proyecto, así que el proyecto DEBE estar en la matriz
            proyecto_val = op.get('proyecto')
            
            if proyecto_val is None:
                ordenes_saltadas += 1
                razones_salto['sin_proyecto'] += 1
                continue
            
            # Convertir a int
            try:
                proyecto_id = int(proyecto_val)
            except (ValueError, TypeError):
                ordenes_saltadas += 1
                razones_salto['proyecto_invalido'] += 1
                continue
            
            # Ya debe estar en la matriz (porque filtramos en la consulta)
            if proyecto_id not in matriz:
                ordenes_saltadas += 1
                razones_salto['proyecto_no_en_matriz'] += 1
                continue
            
            # Normalizar item (igual que en el sistema antiguo)
            item_val = op.get('item')
            if item_val is None:
                ordenes_saltadas += 1
                razones_salto['sin_item'] += 1
                continue
            
            item_id = None
            
            # Si es int, usar directamente
            if isinstance(item_val, int):
                item_id = item_val if item_val in id_to_tipo else None
            else:
                # Normalizar nombre de tipo
                tipo = str(item_val).upper().strip()
                if tipo:
                    if tipo.endswith('S') and len(tipo) > 3:
                        tipo = tipo[:-1]
                    item_id = tipo_to_id.get(tipo)
            
            if not item_id or item_id not in matriz[proyecto_id]['items']:
                ordenes_saltadas += 1
                if not item_id:
                    razones_salto['item_no_normalizado'] += 1
                else:
                    razones_salto['item_no_en_matriz'] += 1
                continue
            
            # Obtener mes - Si no existe, extraer de fecha_factura
            mes = op.get('mes')
            if not mes:
                # Intentar extraer de fecha_factura
                fecha_factura = op.get('fecha_factura')
                if fecha_factura:
                    try:
                        # La fecha viene en formato YYYY-MM-DD o similar
                        if isinstance(fecha_factura, str):
                            # Parsear la fecha
                            fecha_obj = datetime.strptime(fecha_factura.split('T')[0], '%Y-%m-%d')
                            mes = fecha_obj.month
                        else:
                            # Si es un objeto date
                            mes = fecha_factura.month
                    except:
                        ordenes_saltadas += 1
                        razones_salto['mes_invalido'] += 1
                        continue
                else:
                    ordenes_saltadas += 1
                    razones_salto['sin_mes'] += 1
                    continue
            
            try:
                mes = int(mes)
            except (ValueError, TypeError):
                ordenes_saltadas += 1
                razones_salto['mes_invalido'] += 1
                continue
            
            if mes not in matriz[proyecto_id]['items'][item_id]['meses']:
                ordenes_saltadas += 1
                razones_salto['mes_fuera_rango'] += 1
                continue
            
            # Obtener monto
            monto = float(op.get('costo_final_con_iva', 0) or 0)
            
            # APLICAR
            matriz[proyecto_id]['items'][item_id]['meses'][mes]['real'] += monto
            matriz[proyecto_id]['items'][item_id]['total_real'] += monto
            contador_ops += 1

        logger.info(f"✅ Órdenes procesadas: {contador_ops}/{len(ordenes_pago)} aplicadas, {ordenes_saltadas} saltadas")
        
        # LOG TEMPORAL PARA DEBUG
        if ordenes_saltadas > 0:
            logger.warning(f"⚠️ {ordenes_saltadas} órdenes fueron saltadas. Detalle:")
            for razon, cantidad in razones_salto.items():
                if cantidad > 0:
                    logger.warning(f"   - {razon}: {cantidad}")

        # 9. Procesar gastos directos
        contador_gd = 0
        gastos_saltados = 0
        
        # Mapeo de nombres de meses en español a números
        meses_map = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        for gd in gastos_directos:
            proyecto_id = gd.get('proyecto_id')
            item_id = gd.get('item_id')
            mes_val = gd.get('mes')
            
            # Si no hay mes, intentar extraer de la fecha
            if not mes_val:
                fecha = gd.get('fecha')
                if fecha:
                    try:
                        if isinstance(fecha, str):
                            fecha_obj = datetime.strptime(fecha.split('T')[0], '%Y-%m-%d')
                            mes_val = fecha_obj.month
                        else:
                            mes_val = fecha.month
                    except:
                        pass
            
            if not all([proyecto_id, item_id, mes_val]):
                gastos_saltados += 1
                continue
            
            try:
                proyecto_id = int(proyecto_id)
                item_id = int(item_id)
                
                # Intentar convertir mes a int, si falla, buscar en el mapa
                try:
                    mes = int(mes_val)
                except (ValueError, TypeError):
                    # Es un string, normalizar y buscar en el mapa
                    mes_str = str(mes_val).lower().strip()
                    mes = meses_map.get(mes_str)
                    if mes is None:
                        logger.warning(f"⚠️ Mes no reconocido en gasto directo: '{mes_val}'")
                        gastos_saltados += 1
                        continue
                        
            except (ValueError, TypeError):
                gastos_saltados += 1
                continue
                
            if proyecto_id not in matriz or item_id not in matriz[proyecto_id]['items']:
                gastos_saltados += 1
                continue
                
            if mes not in matriz[proyecto_id]['items'][item_id]['meses']:
                gastos_saltados += 1
                continue
            
            monto = float(gd.get('monto', 0) or 0)
            matriz[proyecto_id]['items'][item_id]['meses'][mes]['real'] += monto
            matriz[proyecto_id]['items'][item_id]['total_real'] += monto
            contador_gd += 1

        logger.info(f"✅ Gastos directos: {contador_gd}/{len(gastos_directos)} aplicados, {gastos_saltados} saltados")

        # 10. Calcular diferencias
        for proyecto_id in matriz:
            for item_id in matriz[proyecto_id]['items']:
                for mes in matriz[proyecto_id]['items'][item_id]['meses']:
                    mes_data = matriz[proyecto_id]['items'][item_id]['meses'][mes]
                    mes_data['diferencia'] = mes_data['presupuesto'] - mes_data['real']
                
                item_data = matriz[proyecto_id]['items'][item_id]
                item_data['diferencia'] = item_data['total_presupuesto'] - item_data['total_real']

        # 11. Calcular totales
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
        
        logger.info(f"✅ TOTALES: Presup=${totales['presupuesto_total']:,.0f}, Real=${totales['real_total']:,.0f}")
        
        # 12. Obtener datos de venta y producción de proyectos
        venta_total = 0
        produccion_total = 0
        
        for proyecto in proyectos:
            proyecto_id = proyecto.get('id')
            
            # Venta (desde Supabase)
            venta = proyecto.get('venta')
            if venta:
                try:
                    venta_total += int(venta)
                except (ValueError, TypeError):
                    pass
            
            # Producción (desde Nhost - sistema de producción)
            produccion_nhost = get_produccion_actual_nhost(proyecto_id)
            produccion_total += produccion_nhost
        
        logger.info(f"✅ RESUMEN: Venta=${venta_total:,.0f}, Producción=${produccion_total:,.0f} (desde Nhost)")
        
        # 13. Calcular resúmenes
        resumen = {
            'presupuesto_inicial': {
                'venta': venta_total,
                'gasto': int(totales['presupuesto_total']),
                'saldo': venta_total - int(totales['presupuesto_total'])
            },
            'estado_actual': {
                'produccion': produccion_total,
                'gasto': int(totales['real_total']),
                'saldo': produccion_total - int(totales['real_total'])
            },
            'indicadores': {
                'ejecucion_presupuesto': round((totales['real_total'] / totales['presupuesto_total'] * 100), 1) if totales['presupuesto_total'] > 0 else 0,
                'avance_produccion': round((produccion_total / venta_total * 100), 1) if venta_total > 0 else 0,
                'variacion_saldo': (venta_total - int(totales['presupuesto_total'])) - (produccion_total - int(totales['real_total'])),
                'meses_analizados': len(set(mes for proyecto_id in matriz for item_id in matriz[proyecto_id]['items'] for mes in matriz[proyecto_id]['items'][item_id]['meses']))
            }
        }
        
        logger.info(f"✅ RESUMEN: Venta=${venta_total:,.0f}, Producción=${produccion_total:,.0f}")
        logger.info("=== Consulta completada ===")
        
        return jsonify({
            "success": True,
            "data": {
                "matriz": matriz,
                "proyectos": proyectos,
                "items": items,
                "totales": totales,
                "resumen": resumen
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
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
            "message": "Faltan parámetros"
        }), 400
    
    try:
        proyecto_id = int(proyecto_id)
        item_id = int(item_id)
        mes = int(mes)
        
        # Obtener nombres
        proyecto = supabase.table("proyectos").select("proyecto").eq("id", proyecto_id).execute()
        proyecto_data = proyecto.data if proyecto and hasattr(proyecto, 'data') else []
        nombre_proyecto = proyecto_data[0]['proyecto'] if proyecto_data else f"Proyecto {proyecto_id}"
        
        try:
            item = supabase.table("item").select("tipo").eq("id", item_id).execute()
            item_data = item.data if item and hasattr(item, 'data') else []
        except:
            item = supabase.table("items").select("tipo").eq("id", item_id).execute()
            item_data = item.data if item and hasattr(item, 'data') else []
        
        nombre_item = item_data[0]['tipo'] if item_data else f"Item {item_id}"
        
        # Órdenes de pago - sin filtrar por mes ni fecha_factura inicialmente
        ordenes = (
            supabase.table("orden_de_pago")
            .select("id, orden_numero, orden_compra, costo_final_con_iva, fecha_factura, detalle_compra, proyecto, item, mes")
            .eq("proyecto", proyecto_id)
            .execute()
        )
        ordenes_data = ordenes.data if ordenes and hasattr(ordenes, 'data') else []
        
        # Filtrar por item y mes (con extracción de mes desde fecha_factura si es necesario)
        ordenes_filtradas = []
        for op in ordenes_data:
            item_val = op.get('item')
            if item_val is None:
                continue
            
            # Determinar el mes de la orden
            mes_orden = op.get('mes')
            if not mes_orden:
                # Extraer mes desde fecha_factura
                fecha_factura = op.get('fecha_factura')
                if fecha_factura:
                    try:
                        from datetime import datetime
                        if 'T' in fecha_factura:
                            dt = datetime.fromisoformat(fecha_factura.replace('Z', '+00:00'))
                        else:
                            dt = datetime.strptime(fecha_factura, '%Y-%m-%d')
                        mes_orden = dt.month
                    except:
                        continue
                else:
                    continue
            else:
                try:
                    mes_orden = int(mes_orden)
                except:
                    continue
            
            # Verificar si coincide con el mes buscado
            if mes_orden != mes:
                continue
            
            # Verificar si coincide con el item
            try:
                if int(item_val) == item_id:
                    ordenes_filtradas.append({
                        'id': op.get('id'),
                        'orden_numero': op.get('orden_numero'),
                        'orden_compra': op.get('orden_compra'),
                        'monto': op.get('costo_final_con_iva', 0),
                        'fecha': op.get('fecha_factura'),
                        'descripcion': op.get('detalle_compra', '')
                    })
            except (ValueError, TypeError):
                # Es nombre de tipo
                tipo_op = str(item_val).upper().strip()
                if tipo_op.endswith('S') and len(tipo_op) > 3:
                    tipo_op = tipo_op[:-1]
                tipo_item = nombre_item.upper().strip()
                if tipo_item.endswith('S') and len(tipo_item) > 3:
                    tipo_item = tipo_item[:-1]
                
                if tipo_op == tipo_item:
                    ordenes_filtradas.append({
                        'id': op.get('id'),
                        'orden_numero': op.get('orden_numero'),
                        'orden_compra': op.get('orden_compra'),
                        'monto': op.get('costo_final_con_iva', 0),
                        'fecha': op.get('fecha_factura'),
                        'descripcion': op.get('detalle_compra', '')
                    })
        
        # Gastos directos - sin filtrar por mes inicialmente
        gastos = (
            supabase.table("gastos_directos")
            .select("id, descripcion, monto, fecha, mes")
            .eq("proyecto_id", proyecto_id)
            .eq("item_id", item_id)
            .execute()
        )
        gastos_data = gastos.data if gastos and hasattr(gastos, 'data') else []
        
        # Mapa de nombres de meses en español a números
        meses_map = {
            'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4,
            'Mayo': 5, 'Junio': 6, 'Julio': 7, 'Agosto': 8,
            'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12
        }
        
        # Filtrar por mes (manejando tanto números como nombres)
        gastos_filtrados = []
        for g in gastos_data:
            mes_gasto = g.get('mes')
            mes_num = None
            
            # Intentar convertir mes a número
            if mes_gasto:
                if isinstance(mes_gasto, int):
                    mes_num = mes_gasto
                elif isinstance(mes_gasto, str):
                    # Intentar parsear como entero
                    try:
                        mes_num = int(mes_gasto)
                    except ValueError:
                        # Es un nombre de mes
                        mes_num = meses_map.get(mes_gasto.strip())
            
            # Verificar si coincide con el mes buscado
            if mes_num == mes:
                gastos_filtrados.append({
                    'id': g.get('id'),
                    'descripcion': g.get('descripcion', ''),
                    'monto': g.get('monto', 0),
                    'fecha': g.get('fecha')
                })
        
        total_ordenes = sum(o['monto'] for o in ordenes_filtradas)
        total_gastos = sum(g['monto'] for g in gastos_filtrados)
        
        return jsonify({
            "success": True,
            "data": {
                "proyecto": nombre_proyecto,
                "item": nombre_item,
                "mes": mes,
                "ordenes_pago": ordenes_filtradas,
                "gastos_directos": gastos_filtrados,
                "total_ordenes": total_ordenes,
                "total_gastos": total_gastos,
                "total": total_ordenes + total_gastos
            }
        })
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500