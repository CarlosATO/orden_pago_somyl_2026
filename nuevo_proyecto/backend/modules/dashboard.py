"""
Módulo de Dashboard - KPIs y Analytics
Proporciona datos para el dashboard ejecutivo
"""

from flask import Blueprint, jsonify
from datetime import datetime, timedelta

bp = Blueprint('dashboard', __name__)

# Configuración de Supabase
import os
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)


def calcular_estado_pago(fecha_pago, total_abonado, total_pago):
    """
    Calcular estado del pago (MISMA LÓGICA que pagos.py):
    - pagado: tiene fecha_pago (preferible) O saldo = 0
    - abono: tiene abonos parciales (saldo > 0)
    - pendiente: sin fecha_pago y sin abonos (o con saldo > 0)
    """
    saldo = max(0, total_pago - (total_abonado or 0))

    # Caso 1: Si hay abonos parciales y queda saldo -> ABONO (priorizar abonos)
    if (total_abonado or 0) > 0 and saldo > 0:
        return "abono"

    # Caso 2: Si hay fecha de pago o el saldo es cero -> PAGADO
    if fecha_pago or saldo <= 0:
        return "pagado"

    # Caso 3: Sin fecha, sin abonos, con saldo > 0 -> PENDIENTE
    return "pendiente"


@bp.route('/', methods=['GET'])
def get_dashboard():
    """
    Endpoint principal del dashboard
    GET /api/dashboard/
    """
    try:
        data = obtener_dashboard_completo()
        return jsonify({
            "success": True,
            "data": data
        }), 200
    except Exception as e:
        print(f"Error en get_dashboard: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error al obtener datos del dashboard: {str(e)}"
        }), 500


def obtener_dashboard_completo():
    """
    Obtiene todos los KPIs y datos del dashboard
    """
    try:
        # KPIs principales
        kpis = obtener_kpis_principales()
        
        # Rankings
        top_proveedores = obtener_top_proveedores_deuda()
        top_proyectos = obtener_top_proyectos_criticos()
        
        # Órdenes sin recepcionar
        oc_sin_recepcionar = obtener_oc_sin_recepcionar()
        
        # Gráficos
        evolucion_deuda = obtener_evolucion_deuda()
        distribucion_deuda = obtener_distribucion_deuda_proveedor()
        ejecucion_presupuestaria = obtener_ejecucion_presupuestaria()
        
        return {
            "kpis": kpis,
            "top_proveedores": top_proveedores,
            "top_proyectos": top_proyectos,
            "oc_sin_recepcionar": oc_sin_recepcionar,
            "evolucion_deuda": evolucion_deuda,
            "distribucion_deuda": distribucion_deuda,
            "ejecucion_presupuestaria": ejecucion_presupuestaria
        }
    except Exception as e:
        print(f"Error en obtener_dashboard_completo: {str(e)}")
        raise


def obtener_kpis_principales():
    """
    Calcula los KPIs principales del dashboard
    Usa la MISMA LÓGICA que el módulo de Informe de Pagos
    """
    try:
        # 1. DEUDA TOTAL (Órdenes de Pago pendientes)
        # Obtener TODAS las órdenes de pago (sin filtro de pagado)
        response_op = supabase.table('orden_de_pago').select('*').execute()
        ordenes_pago_raw = response_op.data if response_op.data else []
        
        # Agrupar por orden_numero y sumar montos
        pagos_dict = {}
        for r in ordenes_pago_raw:
            num = r.get("orden_numero")
            if num not in pagos_dict:
                pagos_dict[num] = {
                    "orden_numero": num,
                    "total_pago": 0,
                    "factura": r.get("factura")
                }
            try:
                # IGUAL QUE PAGOS.PY: int redondeado
                monto = int(round(float(r.get("costo_final_con_iva") or 0)))
            except:
                monto = 0
            pagos_dict[num]["total_pago"] += monto
        
        # Obtener fechas de pago
        response_fechas = supabase.table('fechas_de_pagos_op').select('orden_numero, fecha_pago').execute()
        fechas_pago = response_fechas.data if response_fechas.data else []
        
        # IGUAL QUE PAGOS.PY: Doble clave (string e int) para evitar problemas de tipo
        fecha_map = {}
        for f in fechas_pago:
            k = f.get("orden_numero")
            v = f.get("fecha_pago")
            if k is None:
                continue
            fecha_map[str(k)] = v
            try:
                fecha_map[int(k)] = v
            except:
                pass
        
        # Obtener abonos
        response_abonos = supabase.table('abonos_op').select('orden_numero, monto_abono').execute()
        abonos_data = response_abonos.data if response_abonos.data else []
        
        # IGUAL QUE PAGOS.PY: Doble clave y int redondeado
        abonos_map = {}
        for ab in abonos_data:
            num = ab.get("orden_numero")
            try:
                monto = int(round(float(ab.get("monto_abono") or 0)))
            except:
                monto = 0
            if num is None:
                continue
            abonos_map[num] = abonos_map.get(num, 0) + monto
            try:
                abonos_map[int(num)] = abonos_map.get(int(num), 0) + monto
            except:
                pass
        
        # Calcular deuda REAL usando la función calcular_estado_pago
        deuda_total = 0
        deuda_con_factura = 0
        deuda_sin_factura = 0
        cantidad_pendientes = 0  # Cuenta "pendiente" + "abono" (cualquiera que no sea "pagado")
        
        for num, pago in pagos_dict.items():
            total_pago = pago["total_pago"]
            total_abonado = abonos_map.get(num, 0)
            fecha_pago = fecha_map.get(num)
            
            # Calcular saldo
            saldo = max(0, total_pago - total_abonado) if not fecha_pago else 0
            
            # Usar la MISMA función que Informe de Pagos
            estado = calcular_estado_pago(fecha_pago, total_abonado, total_pago)
            
            # IGUAL QUE PAGOS.PY: Contar todo lo que NO sea "pagado"
            if estado != "pagado":
                cantidad_pendientes += 1
                deuda_total += saldo
                
                if pago.get("factura"):
                    deuda_con_factura += saldo
                else:
                    deuda_sin_factura += saldo
        
        # 2. SALDO PRESUPUESTARIO TOTAL
        response_ppto = supabase.table('presupuesto').select('*').execute()
        presupuestos = response_ppto.data if response_ppto.data else []
        
        saldo_presupuestario_total = 0
        proyectos_en_riesgo = 0
        
        for ppto in presupuestos:
            presupuesto = float(ppto.get('presupuesto', 0) or 0)
            real = float(ppto.get('real', 0) or 0)
            saldo = presupuesto - real
            saldo_presupuestario_total += saldo
            
            if saldo < 0:
                proyectos_en_riesgo += 1
        
        # 3. DOCUMENTOS PENDIENTES
        # Facturas sin registrar (OP sin factura con saldo pendiente)
        facturas_pendientes = 0
        for num, pago in pagos_dict.items():
            total_pago = pago["total_pago"]
            total_abonado = abonos_map.get(num, 0)
            fecha_pago = fecha_map.get(num)
            
            if not fecha_pago:  # No está pagado
                saldo = max(0, total_pago - total_abonado)
                if saldo > 0 and not pago.get("factura"):
                    facturas_pendientes += 1
        
        # Órdenes sin recepcionar (>15 días)
        response_oc = supabase.table('orden_de_compra').select('*').execute()
        ordenes = response_oc.data if response_oc.data else []
        
        oc_antiguas = 0
        fecha_limite = datetime.now() - timedelta(days=15)
        
        for oc in ordenes:
            if oc.get('estado') != 'Recepcionada' and oc.get('fecha_emision'):
                try:
                    fecha_emision = datetime.fromisoformat(oc['fecha_emision'].replace('Z', '+00:00'))
                    if fecha_emision < fecha_limite:
                        oc_antiguas += 1
                except:
                    pass
        
        # Pagos vencidos (necesitamos obtener vencimiento de orden_de_pago)
        # Contar órdenes con vencimiento pasado y saldo pendiente
        pagos_vencidos = 0
        fecha_hoy = datetime.now()
        
        # Crear map de vencimientos desde ordenes_pago_raw
        vencimiento_map = {}
        for r in ordenes_pago_raw:
            num = r.get("orden_numero")
            venc = r.get("vencimiento")
            if num and venc and num not in vencimiento_map:
                vencimiento_map[num] = venc
        
        for num, pago in pagos_dict.items():
            total_pago = pago["total_pago"]
            total_abonado = abonos_map.get(num, 0)
            fecha_pago = fecha_map.get(num)
            vencimiento = vencimiento_map.get(num)
            
            if not fecha_pago and vencimiento:  # No pagado y tiene vencimiento
                saldo = max(0, total_pago - total_abonado)
                if saldo > 0:
                    try:
                        fecha_venc = datetime.fromisoformat(vencimiento.replace('Z', '+00:00'))
                        if fecha_venc < fecha_hoy:
                            pagos_vencidos += 1
                    except:
                        pass
        
        documentos_pendientes = facturas_pendientes + oc_antiguas + pagos_vencidos
        
        # 4. MÉTRICAS OPERACIONALES DEL MES ACTUAL
        fecha_inicio_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # OC del mes
        oc_mes_actual = 0
        monto_oc_mes = 0
        for oc in ordenes:
            if oc.get('fecha_emision'):
                try:
                    fecha = datetime.fromisoformat(oc['fecha_emision'].replace('Z', '+00:00'))
                    if fecha >= fecha_inicio_mes:
                        oc_mes_actual += 1
                        monto_oc_mes += float(oc.get('monto_total', 0) or 0)
                except:
                    pass
        
        # Recepciones del mes (ingresos)
        response_ingresos = supabase.table('ingresos').select('*').execute()
        ingresos = response_ingresos.data if response_ingresos.data else []
        
        recepciones_mes = 0
        for ingreso in ingresos:
            if ingreso.get('fecha_recepcion'):
                try:
                    fecha = datetime.fromisoformat(ingreso['fecha_recepcion'].replace('Z', '+00:00'))
                    if fecha >= fecha_inicio_mes:
                        recepciones_mes += 1
                except:
                    pass
        
        # Pagos del mes
        response_pagos = supabase.table('fechas_de_pagos_op').select('*').execute()
        pagos = response_pagos.data if response_pagos.data else []
        
        pagos_mes = 0
        monto_pagos_mes = 0
        for pago in pagos:
            if pago.get('fecha_pago'):
                try:
                    fecha = datetime.fromisoformat(pago['fecha_pago'].replace('Z', '+00:00'))
                    if fecha >= fecha_inicio_mes:
                        pagos_mes += 1
                        monto_pagos_mes += float(pago.get('monto', 0) or 0)
                except:
                    pass
        
        return {
            "deuda_total": round(deuda_total, 2),
            "deuda_con_factura": round(deuda_con_factura, 2),
            "deuda_sin_factura": round(deuda_sin_factura, 2),
            "cantidad_pendientes": cantidad_pendientes,
            "saldo_presupuestario_total": round(saldo_presupuestario_total, 2),
            "proyectos_en_riesgo": proyectos_en_riesgo,
            "documentos_pendientes": documentos_pendientes,
            "facturas_pendientes": facturas_pendientes,
            "oc_antiguas": oc_antiguas,
            "pagos_vencidos": pagos_vencidos,
            "oc_mes_actual": oc_mes_actual,
            "monto_oc_mes": round(monto_oc_mes, 2),
            "recepciones_mes": recepciones_mes,
            "pagos_mes": pagos_mes,
            "monto_pagos_mes": round(monto_pagos_mes, 2)
        }
    except Exception as e:
        print(f"Error en obtener_kpis_principales: {str(e)}")
        raise


def obtener_top_proveedores_deuda():
    """
    Top 5 proveedores con mayor deuda
    """
    try:
        response = supabase.table('orden_de_pago').select('*').execute()
        ordenes_pago = response.data if response.data else []
        
        # Agrupar por proveedor
        deuda_por_proveedor = {}
        
        for op in ordenes_pago:
            if not op.get('pagado', False):  # Solo OP pendientes
                proveedor = op.get('proveedor_nombre', 'Sin Proveedor')
                monto = float(op.get('monto_total', 0) or 0)
                
                if proveedor not in deuda_por_proveedor:
                    deuda_por_proveedor[proveedor] = {
                        'proveedor': proveedor,
                        'deuda': 0,
                        'num_op': 0
                    }
                
                deuda_por_proveedor[proveedor]['deuda'] += monto
                deuda_por_proveedor[proveedor]['num_op'] += 1
        
        # Ordenar y tomar top 5
        top_proveedores = sorted(
            deuda_por_proveedor.values(),
            key=lambda x: x['deuda'],
            reverse=True
        )[:5]
        
        # Redondear montos
        for prov in top_proveedores:
            prov['deuda'] = round(prov['deuda'], 2)
        
        return top_proveedores
    except Exception as e:
        print(f"Error en obtener_top_proveedores_deuda: {str(e)}")
        return []


def obtener_top_proyectos_criticos():
    """
    Top 5 proyectos con mayor deuda y situación presupuestaria crítica
    """
    try:
        # Obtener órdenes de pago
        response_op = supabase.table('orden_de_pago').select('*').execute()
        ordenes_pago = response_op.data if response_op.data else []
        
        # Obtener presupuestos
        response_ppto = supabase.table('presupuesto').select('*').execute()
        presupuestos = response_ppto.data if response_ppto.data else []
        
        # Crear mapa de presupuestos por proyecto
        ppto_por_proyecto = {}
        for ppto in presupuestos:
            proyecto_id = ppto.get('proyecto_id')
            if proyecto_id:
                presupuesto = float(ppto.get('presupuesto', 0) or 0)
                real = float(ppto.get('real', 0) or 0)
                saldo = presupuesto - real
                
                if proyecto_id not in ppto_por_proyecto:
                    ppto_por_proyecto[proyecto_id] = {
                        'presupuesto': 0,
                        'real': 0,
                        'saldo': 0
                    }
                
                ppto_por_proyecto[proyecto_id]['presupuesto'] += presupuesto
                ppto_por_proyecto[proyecto_id]['real'] += real
                ppto_por_proyecto[proyecto_id]['saldo'] += saldo
        
        # Agrupar deuda por proyecto
        deuda_por_proyecto = {}
        
        for op in ordenes_pago:
            if not op.get('pagado', False):  # Solo OP pendientes
                proyecto_id = op.get('proyecto_id')
                proyecto_nombre = op.get('proyecto_nombre', 'Sin Proyecto')
                monto = float(op.get('monto_total', 0) or 0)
                
                if proyecto_id not in deuda_por_proyecto:
                    deuda_por_proyecto[proyecto_id] = {
                        'proyecto_id': proyecto_id,
                        'proyecto': proyecto_nombre,
                        'deuda': 0,
                        'num_op': 0,
                        'saldo_presupuesto': 0
                    }
                
                deuda_por_proyecto[proyecto_id]['deuda'] += monto
                deuda_por_proyecto[proyecto_id]['num_op'] += 1
        
        # Agregar información presupuestaria
        for proyecto_id, data in deuda_por_proyecto.items():
            if proyecto_id in ppto_por_proyecto:
                data['saldo_presupuesto'] = ppto_por_proyecto[proyecto_id]['saldo']
            
            # Determinar estado
            if data['saldo_presupuesto'] < 0:
                data['estado'] = 'riesgo'
            elif data['saldo_presupuesto'] < data['deuda'] * 0.2:  # Menos del 20% de margen
                data['estado'] = 'alerta'
            else:
                data['estado'] = 'ok'
        
        # Ordenar por deuda y tomar top 5
        top_proyectos = sorted(
            deuda_por_proyecto.values(),
            key=lambda x: x['deuda'],
            reverse=True
        )[:5]
        
        # Redondear montos
        for proy in top_proyectos:
            proy['deuda'] = round(proy['deuda'], 2)
            proy['saldo_presupuesto'] = round(proy['saldo_presupuesto'], 2)
        
        return top_proyectos
    except Exception as e:
        print(f"Error en obtener_top_proyectos_criticos: {str(e)}")
        return []


def obtener_oc_sin_recepcionar():
    """
    Órdenes de compra sin recepcionar (>15 días)
    """
    try:
        response = supabase.table('orden_de_compra').select('*').execute()
        ordenes = response.data if response.data else []
        
        oc_pendientes = []
        fecha_limite = datetime.now() - timedelta(days=15)
        
        for oc in ordenes:
            if oc.get('estado') != 'Recepcionada' and oc.get('fecha_emision'):
                try:
                    fecha_emision = datetime.fromisoformat(oc['fecha_emision'].replace('Z', '+00:00'))
                    if fecha_emision < fecha_limite:
                        dias_pendiente = (datetime.now() - fecha_emision).days
                        
                        oc_pendientes.append({
                            'numero_orden': oc.get('numero_orden', 'N/A'),
                            'proveedor': oc.get('proveedor_nombre', 'Sin Proveedor'),
                            'proyecto': oc.get('proyecto_nombre', 'Sin Proyecto'),
                            'monto_total': round(float(oc.get('monto_total', 0) or 0), 2),
                            'fecha_emision': oc.get('fecha_emision'),
                            'dias_pendiente': dias_pendiente,
                            'estado': oc.get('estado', 'Pendiente')
                        })
                except:
                    pass
        
        # Ordenar por días pendiente (más antiguos primero)
        oc_pendientes.sort(key=lambda x: x['dias_pendiente'], reverse=True)
        
        return oc_pendientes[:10]  # Top 10
    except Exception as e:
        print(f"Error en obtener_oc_sin_recepcionar: {str(e)}")
        return []


def obtener_evolucion_deuda():
    """
    Evolución de la deuda en los últimos 6 meses
    """
    try:
        response = supabase.table('orden_de_pago').select('*').execute()
        ordenes_pago = response.data if response.data else []
        
        # Calcular deuda por mes (últimos 6 meses)
        evolucion = []
        fecha_actual = datetime.now()
        
        meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                         'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        
        for i in range(5, -1, -1):  # 6 meses atrás hasta hoy
            # Calcular fecha de corte del mes
            if fecha_actual.month - i > 0:
                mes = fecha_actual.month - i
                anio = fecha_actual.year
            else:
                mes = 12 + (fecha_actual.month - i)
                anio = fecha_actual.year - 1
            
            fecha_corte = datetime(anio, mes, 28, 23, 59, 59)  # Último día del mes (aprox)
            
            # Calcular deuda pendiente a esa fecha
            deuda_mes = 0
            for op in ordenes_pago:
                if op.get('fecha_creacion'):
                    try:
                        fecha_creacion = datetime.fromisoformat(op['fecha_creacion'].replace('Z', '+00:00'))
                        
                        # OP creada antes del corte
                        if fecha_creacion <= fecha_corte:
                            # Si tiene pago, verificar que fue después del corte
                            pagado_despues = False
                            if op.get('pagado', False) and op.get('fecha_pago'):
                                fecha_pago = datetime.fromisoformat(op['fecha_pago'].replace('Z', '+00:00'))
                                if fecha_pago > fecha_corte:
                                    pagado_despues = True
                            
                            # Si no estaba pagada al corte, contar
                            if not op.get('pagado', False) or pagado_despues:
                                deuda_mes += float(op.get('monto_total', 0) or 0)
                    except:
                        pass
            
            evolucion.append({
                'mes': meses_nombres[mes - 1],
                'deuda': round(deuda_mes, 2)
            })
        
        return evolucion
    except Exception as e:
        print(f"Error en obtener_evolucion_deuda: {str(e)}")
        return []


def obtener_distribucion_deuda_proveedor():
    """
    Distribución de deuda por proveedor (para gráfico pie)
    """
    try:
        top_proveedores = obtener_top_proveedores_deuda()
        
        if not top_proveedores:
            return []
        
        # Calcular total para porcentajes
        total_deuda = sum(p['deuda'] for p in top_proveedores)
        
        distribucion = []
        for prov in top_proveedores:
            porcentaje = (prov['deuda'] / total_deuda * 100) if total_deuda > 0 else 0
            distribucion.append({
                'proveedor': prov['proveedor'],
                'deuda': prov['deuda'],
                'porcentaje': round(porcentaje, 1)
            })
        
        return distribucion
    except Exception as e:
        print(f"Error en obtener_distribucion_deuda_proveedor: {str(e)}")
        return []


def obtener_ejecucion_presupuestaria():
    """
    Ejecución presupuestaria por proyecto (para gráfico barras)
    """
    try:
        response = supabase.table('presupuesto').select('*').execute()
        presupuestos = response.data if response.data else []
        
        # Obtener nombres de proyectos
        response_proy = supabase.table('proyectos').select('id, nombre').execute()
        proyectos = response_proy.data if response_proy.data else []
        proyecto_nombres = {p['id']: p['nombre'] for p in proyectos}
        
        # Agrupar por proyecto
        ejecucion_por_proyecto = {}
        
        for ppto in presupuestos:
            proyecto_id = ppto.get('proyecto_id')
            if proyecto_id:
                presupuesto = float(ppto.get('presupuesto', 0) or 0)
                real = float(ppto.get('real', 0) or 0)
                
                if proyecto_id not in ejecucion_por_proyecto:
                    ejecucion_por_proyecto[proyecto_id] = {
                        'proyecto': proyecto_nombres.get(proyecto_id, f'Proyecto {proyecto_id}'),
                        'presupuesto': 0,
                        'real': 0,
                        'saldo': 0
                    }
                
                ejecucion_por_proyecto[proyecto_id]['presupuesto'] += presupuesto
                ejecucion_por_proyecto[proyecto_id]['real'] += real
        
        # Calcular saldos y ordenar
        ejecucion = []
        for data in ejecucion_por_proyecto.values():
            data['saldo'] = data['presupuesto'] - data['real']
            data['presupuesto'] = round(data['presupuesto'], 2)
            data['real'] = round(data['real'], 2)
            data['saldo'] = round(data['saldo'], 2)
            data['porcentaje_ejecutado'] = round((data['real'] / data['presupuesto'] * 100) if data['presupuesto'] > 0 else 0, 1)
            ejecucion.append(data)
        
        # Ordenar por presupuesto (proyectos más grandes primero)
        ejecucion.sort(key=lambda x: x['presupuesto'], reverse=True)
        
        return ejecucion[:10]  # Top 10 proyectos
    except Exception as e:
        print(f"Error en obtener_ejecucion_presupuestaria: {str(e)}")
        return []
