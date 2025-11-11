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


@bp.route('/documentos-pendientes-detalle', methods=['GET'])
def get_documentos_pendientes_detalle():
    """
    Obtiene TODOS los pagos pendientes (sin fecha_pago y con saldo > 0) para modal y PDF
    GET /api/dashboard/documentos-pendientes-detalle
    """
    try:
        from flask import current_app
        
        # Obtener datos CON PAGINACIÓN para obtener TODOS los registros
        print("🔍 Obteniendo datos de documentos pendientes con paginación...")
        
        # orden_de_pago - PAGINADO
        page_size = 1000
        offset = 0
        ordenes_pago_raw = []
        while True:
            batch = supabase.table('orden_de_pago').select('*').range(offset, offset + page_size - 1).execute().data or []
            ordenes_pago_raw.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        print(f"✅ orden_de_pago: {len(ordenes_pago_raw)} filas obtenidas")
        
        # fechas_de_pagos_op - PAGINADO
        offset = 0
        fechas_pago = []
        while True:
            batch = supabase.table('fechas_de_pagos_op').select('*').range(offset, offset + page_size - 1).execute().data or []
            fechas_pago.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        print(f"✅ fechas_de_pagos_op: {len(fechas_pago)} filas obtenidas")
        
        # abonos_op - PAGINADO
        offset = 0
        abonos_data = []
        while True:
            batch = supabase.table('abonos_op').select('*').range(offset, offset + page_size - 1).execute().data or []
            abonos_data.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        print(f"✅ abonos_op: {len(abonos_data)} filas obtenidas")
        
        # Obtener proyectos para mapear IDs a nombres
        response_proy = supabase.table('proyectos').select('id, proyecto').execute()
        proyectos = response_proy.data if response_proy.data else []
        proyecto_map = {p["id"]: p["proyecto"] for p in proyectos}
        print(f"✅ proyectos: {len(proyectos)} proyectos mapeados")
        
        # Crear maps
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
        
        print(f"✅ Fechas de pago mapeadas: {len(fecha_map)} órdenes con fecha_pago")
        
        abonos_map = {}
        for ab in abonos_data:
            num = ab.get("orden_numero")
            try:
                monto = int(round(float(ab.get("monto_abono") or 0)))
            except:
                monto = 0
            if num is None:
                continue
            try:
                num_int = int(num)
                abonos_map[num_int] = abonos_map.get(num_int, 0) + monto
            except:
                abonos_map[num] = abonos_map.get(num, 0) + monto
        
        print(f"✅ Abonos mapeados: {len(abonos_map)} órdenes con abonos")
        
        # Agrupar por orden_numero
        pagos_dict = {}
        for r in ordenes_pago_raw:
            num = r.get("orden_numero")
            if num not in pagos_dict:
                proyecto_id = r.get("proyecto")
                proyecto_nombre = proyecto_map.get(proyecto_id, f"Proyecto {proyecto_id}" if proyecto_id else "---")
                
                pagos_dict[num] = {
                    "orden_numero": num,
                    "proveedor": r.get("proveedor_nombre", "---"),
                    "proyecto": proyecto_nombre,
                    "proyecto_id": proyecto_id,
                    "factura": r.get("factura"),
                    "vencimiento": r.get("vencimiento"),
                    "fecha_op": r.get("fecha"),  # Fecha de la orden de pago
                    "total_pago": 0
                }
            try:
                monto = int(round(float(r.get("costo_final_con_iva") or 0)))
            except:
                monto = 0
            pagos_dict[num]["total_pago"] += monto
        
        # TODOS los pagos pendientes (sin fecha de pago y con saldo pendiente)
        pagos_pendientes = []
        pagos_con_abonos = []
        fecha_hoy = datetime.now()
        
        print(f"\n🔍 Filtrando documentos pendientes...")
        debug_ordenes = [3050, 3055, 2242]  # Órdenes de ejemplo para debug
        
        for num, pago in pagos_dict.items():
            total_pago = pago["total_pago"]
            total_abonado = abonos_map.get(num, 0)
            fecha_pago = fecha_map.get(num)
            vencimiento = pago.get("vencimiento")
            
            # Debug para órdenes específicas
            if num in debug_ordenes:
                print(f"\n📌 OP {num}:")
                print(f"   Total: ${total_pago:,.0f}")
                print(f"   Abonado: ${total_abonado:,.0f}")
                print(f"   Fecha pago (pagado): {fecha_pago}")
                print(f"   Fecha OP: {pago.get('fecha_op')}")
                print(f"   Vencimiento (fecha límite): {vencimiento}")
                if vencimiento:
                    try:
                        fv = datetime.fromisoformat(vencimiento.replace('Z', '+00:00'))
                        dias = (fecha_hoy - fv).days
                        print(f"   Días desde vencimiento: {dias}")
                    except:
                        print(f"   Error parseando vencimiento")
            
            # Si NO tiene fecha de pago y tiene saldo pendiente
            if not fecha_pago:
                saldo = max(0, total_pago - total_abonado)
                if saldo > 0:
                    # Calcular días de atraso usando VENCIMIENTO (fecha comprometida de pago)
                    dias_atraso = 0
                    tipo_pago = "Pendiente"
                    estado = "pendiente"
                    fecha_vencimiento_formatted = "---"
                    
                    if vencimiento:
                        try:
                            # Parsear fecha de vencimiento (fecha comprometida de pago)
                            fecha_venc = datetime.fromisoformat(vencimiento.replace('Z', '+00:00'))
                            # Formatear a formato chileno DD/MM/YYYY
                            fecha_vencimiento_formatted = fecha_venc.strftime('%d/%m/%Y')
                            
                            # Comparar fecha de vencimiento con hoy
                            if fecha_venc.date() < fecha_hoy.date():
                                # Ya pasó la fecha comprometida = HAY ATRASO
                                dias_atraso = (fecha_hoy.date() - fecha_venc.date()).days
                                tipo_pago = f"Vencido ({dias_atraso} días)"
                                estado = "vencido"
                            else:
                                # Aún no vence
                                dias_para_vencer = (fecha_venc.date() - fecha_hoy.date()).days
                                tipo_pago = f"Pendiente (vence en {dias_para_vencer} días)"
                        except Exception as e:
                            print(f"⚠️ Error parseando vencimiento para OP {num}: {e}")
                    
                    # Formatear fecha_op a formato chileno
                    fecha_op_formatted = "---"
                    if pago.get("fecha_op"):
                        try:
                            fecha_op_dt = datetime.fromisoformat(str(pago.get("fecha_op")).replace('Z', '+00:00'))
                            fecha_op_formatted = fecha_op_dt.strftime('%d/%m/%Y')
                        except:
                            fecha_op_formatted = str(pago.get("fecha_op"))[:10]  # Fallback
                    
                    documento = {
                        "orden_numero": num,
                        "proveedor": pago["proveedor"],
                        "proyecto": pago["proyecto"],
                        "factura": pago.get("factura", "---"),
                        "fecha_op": fecha_op_formatted,  # Formato DD/MM/YYYY
                        "monto_total": round(total_pago, 2),
                        "total_abonado": round(total_abonado, 2),
                        "saldo": round(saldo, 2),
                        "dias_atraso": dias_atraso,
                        "fecha_vencimiento": fecha_vencimiento_formatted,  # Formato DD/MM/YYYY
                        "tipo": tipo_pago,
                        "estado": estado
                    }
                    
                    # Clasificar: con abonos o pendiente
                    if total_abonado > 0:
                        pagos_con_abonos.append(documento)
                    else:
                        pagos_pendientes.append(documento)
        
        # Ordenar por días de atraso (más críticos primero)
        pagos_pendientes.sort(key=lambda x: x['dias_atraso'], reverse=True)
        pagos_con_abonos.sort(key=lambda x: x['dias_atraso'], reverse=True)
        
        # Combinar todos
        todos_documentos = pagos_pendientes + pagos_con_abonos
        
        print(f"\n📊 RESULTADO DOCUMENTOS PENDIENTES:")
        print(f"   • Total órdenes procesadas: {len(pagos_dict)}")
        print(f"   • Total documentos pendientes: {len(todos_documentos)}")
        print(f"   • Pendientes sin abonos: {len(pagos_pendientes)}")
        print(f"   • Con abonos parciales: {len(pagos_con_abonos)}")
        print(f"   • Vencidos: {sum(1 for d in todos_documentos if d['estado'] == 'vencido')}")
        
        return jsonify({
            "success": True,
            "data": {
                "documentos": todos_documentos,
                "pendientes": pagos_pendientes,
                "con_abonos": pagos_con_abonos,
                "stats": {
                    "total": len(todos_documentos),
                    "pendientes": len(pagos_pendientes),
                    "con_abonos": len(pagos_con_abonos),
                    "vencidos": sum(1 for d in todos_documentos if d['estado'] == 'vencido')
                }
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error en get_documentos_pendientes_detalle: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error al obtener detalle de documentos pendientes: {str(e)}"
        }), 500


@bp.route('/documentos-pendientes-pdf', methods=['GET'])
def generar_pdf_documentos_pendientes():
    """
    Genera y descarga un PDF con todos los documentos pendientes
    GET /api/dashboard/documentos-pendientes-pdf
    """
    try:
        from flask import current_app, send_file
        from backend.pdf.documentos_pendientes_pdf import generar_pdf_documentos_pendientes
        import tempfile
        
        print("🔍 Generando PDF de documentos pendientes...")
        
        # Obtener datos CON PAGINACIÓN (igual que documentos-pendientes-detalle)
        page_size = 1000
        offset = 0
        ordenes_pago_raw = []
        while True:
            batch = supabase.table('orden_de_pago').select('*').range(offset, offset + page_size - 1).execute().data or []
            ordenes_pago_raw.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        
        offset = 0
        fechas_pago = []
        while True:
            batch = supabase.table('fechas_de_pagos_op').select('*').range(offset, offset + page_size - 1).execute().data or []
            fechas_pago.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        
        offset = 0
        abonos_data = []
        while True:
            batch = supabase.table('abonos_op').select('*').range(offset, offset + page_size - 1).execute().data or []
            abonos_data.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        
        # Obtener proyectos
        response_proy = supabase.table('proyectos').select('id, proyecto').execute()
        proyectos = response_proy.data if response_proy.data else []
        proyecto_map = {p["id"]: p["proyecto"] for p in proyectos}
        
        # Crear maps (igual que en documentos-pendientes-detalle)
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
        
        abonos_map = {}
        for ab in abonos_data:
            num = ab.get("orden_numero")
            try:
                monto = int(round(float(ab.get("monto_abono") or 0)))
            except:
                monto = 0
            if num is None:
                continue
            try:
                num_int = int(num)
                abonos_map[num_int] = abonos_map.get(num_int, 0) + monto
            except:
                abonos_map[num] = abonos_map.get(num, 0) + monto
        
        # Agrupar por orden_numero
        pagos_dict = {}
        for r in ordenes_pago_raw:
            num = r.get("orden_numero")
            if num not in pagos_dict:
                proyecto_id = r.get("proyecto")
                proyecto_nombre = proyecto_map.get(proyecto_id, f"Proyecto {proyecto_id}" if proyecto_id else "---")
                
                pagos_dict[num] = {
                    "orden_numero": num,
                    "proveedor": r.get("proveedor_nombre", "---"),
                    "proyecto": proyecto_nombre,
                    "factura": r.get("factura"),
                    "vencimiento": r.get("vencimiento"),
                    "fecha_op": r.get("fecha"),
                    "total_pago": 0
                }
            try:
                monto = int(round(float(r.get("costo_final_con_iva") or 0)))
            except:
                monto = 0
            pagos_dict[num]["total_pago"] += monto
        
        # Filtrar documentos pendientes
        pagos_pendientes = []
        pagos_con_abonos = []
        fecha_hoy = datetime.now()
        
        for num, pago in pagos_dict.items():
            total_pago = pago["total_pago"]
            total_abonado = abonos_map.get(num, 0)
            fecha_pago = fecha_map.get(num)
            vencimiento = pago.get("vencimiento")
            
            if not fecha_pago:
                saldo = max(0, total_pago - total_abonado)
                if saldo > 0:
                    dias_atraso = 0
                    tipo_pago = "Pendiente"
                    estado = "pendiente"
                    fecha_vencimiento_formatted = "---"
                    
                    if vencimiento:
                        try:
                            fecha_venc = datetime.fromisoformat(vencimiento.replace('Z', '+00:00'))
                            fecha_vencimiento_formatted = fecha_venc.strftime('%d/%m/%Y')
                            
                            if fecha_venc.date() < fecha_hoy.date():
                                dias_atraso = (fecha_hoy.date() - fecha_venc.date()).days
                                tipo_pago = f"Vencido ({dias_atraso} días)"
                                estado = "vencido"
                            else:
                                dias_para_vencer = (fecha_venc.date() - fecha_hoy.date()).days
                                tipo_pago = f"Pendiente (vence en {dias_para_vencer} días)"
                        except:
                            pass
                    
                    fecha_op_formatted = "---"
                    if pago.get("fecha_op"):
                        try:
                            fecha_op_dt = datetime.fromisoformat(str(pago.get("fecha_op")).replace('Z', '+00:00'))
                            fecha_op_formatted = fecha_op_dt.strftime('%d/%m/%Y')
                        except:
                            fecha_op_formatted = str(pago.get("fecha_op"))[:10]
                    
                    documento = {
                        "orden_numero": num,
                        "proveedor": pago["proveedor"],
                        "proyecto": pago["proyecto"],
                        "factura": pago.get("factura", "---"),
                        "fecha_op": fecha_op_formatted,
                        "monto_total": round(total_pago, 2),
                        "total_abonado": round(total_abonado, 2),
                        "saldo": round(saldo, 2),
                        "dias_atraso": dias_atraso,
                        "fecha_vencimiento": fecha_vencimiento_formatted,
                        "tipo": tipo_pago,
                        "estado": estado
                    }
                    
                    if total_abonado > 0:
                        pagos_con_abonos.append(documento)
                    else:
                        pagos_pendientes.append(documento)
        
        pagos_pendientes.sort(key=lambda x: x['dias_atraso'], reverse=True)
        pagos_con_abonos.sort(key=lambda x: x['dias_atraso'], reverse=True)
        todos_documentos = pagos_pendientes + pagos_con_abonos
        
        stats = {
            "total": len(todos_documentos),
            "pendientes": len(pagos_pendientes),
            "con_abonos": len(pagos_con_abonos),
            "vencidos": sum(1 for d in todos_documentos if d['estado'] == 'vencido')
        }
        
        print(f"✅ {len(todos_documentos)} documentos pendientes para PDF")
        
        # Generar PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            pdf_path = tmp.name
        
        generar_pdf_documentos_pendientes(todos_documentos, stats, pdf_path)
        
        # Nombre del archivo para descarga
        fecha_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"documentos_pendientes_{fecha_str}.pdf"
        
        print(f"✅ PDF generado: {filename}")
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error generando PDF: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": f"Error al generar PDF: {str(e)}"
        }), 500


def obtener_dashboard_completo():
    """
    Obtiene todos los KPIs y datos del dashboard
    """
    try:
        # Prefetch tablas comunes CON PAGINACIÓN para obtener TODOS los registros
        # orden_de_pago - PAGINADO
        page_size = 1000
        offset = 0
        ordenes_pago_raw = []
        while True:
            batch = supabase.table('orden_de_pago').select('*').range(offset, offset + page_size - 1).execute().data or []
            ordenes_pago_raw.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        print(f"✅ PREFETCH orden_de_pago: {len(ordenes_pago_raw)} filas obtenidas")

        # fechas_de_pagos_op - PAGINADO
        offset = 0
        fechas_pago = []
        while True:
            batch = supabase.table('fechas_de_pagos_op').select('*').range(offset, offset + page_size - 1).execute().data or []
            fechas_pago.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size

        # abonos_op - PAGINADO
        offset = 0
        abonos_data = []
        while True:
            batch = supabase.table('abonos_op').select('*').range(offset, offset + page_size - 1).execute().data or []
            abonos_data.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size

        response_ppto = supabase.table('presupuesto').select('*').execute()
        presupuestos = response_ppto.data if response_ppto.data else []

        response_oc = supabase.table('orden_de_compra').select('*').execute()
        ordenes = response_oc.data if response_oc.data else []

        response_ingresos = supabase.table('ingresos').select('*').execute()
        ingresos = response_ingresos.data if response_ingresos.data else []

        response_proy = supabase.table('proyectos').select('*').execute()
        proyectos = response_proy.data if response_proy.data else []

        prefetch = {
            'orden_de_pago': ordenes_pago_raw,
            'fechas_de_pagos_op': fechas_pago,
            'abonos_op': abonos_data,
            'presupuesto': presupuestos,
            'orden_de_compra': ordenes,
            'ingresos': ingresos,
            'proyectos': proyectos
        }

        # KPIs principales (usar datos prefeteched)
        kpis = obtener_kpis_principales(prefetch=prefetch)

        # Rankings
        top_proveedores = obtener_top_proveedores_deuda(prefetch=prefetch)
        top_proyectos = obtener_top_proyectos_criticos(prefetch=prefetch)

        # Órdenes sin recepcionar
        oc_sin_recepcionar = obtener_oc_sin_recepcionar(prefetch=prefetch)

        # Gráficos
        evolucion_deuda = obtener_evolucion_deuda(prefetch=prefetch)
        distribucion_deuda = obtener_distribucion_deuda_proveedor(prefetch=prefetch)
        ejecucion_presupuestaria = obtener_ejecucion_presupuestaria(prefetch=prefetch)
        
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


def obtener_kpis_principales(prefetch=None):
    """
    Calcula los KPIs principales del dashboard
    Usa la MISMA LÓGICA EXACTA que el módulo de Informe de Pagos (sin filtros)
    """
    print("=" * 80)
    print("🚨 FUNCIÓN obtener_kpis_principales INICIADA - VERSIÓN NUEVA")
    print("=" * 80)
    
    try:
        # Obtener TODAS las filas de orden_de_pago
        if prefetch and 'orden_de_pago' in prefetch:
            all_rows = prefetch.get('orden_de_pago') or []
            print(f"📦 Usando PREFETCH: {len(all_rows)} filas")
        else:
            page_size = 1000
            offset = 0
            all_rows = []
            while True:
                res = supabase.table("orden_de_pago").select(
                    "orden_numero, costo_final_con_iva, proyecto"
                ).order("orden_numero", desc=True).range(offset, offset + page_size - 1).execute()
                batch = res.data or []
                all_rows.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size
            print(f"📦 Query paginado: {len(all_rows)} filas")
        
        print(f"✅ Total de filas obtenidas: {len(all_rows)}")
        
        # Agrupar por orden_numero (IGUAL QUE PAGOS.PY)
        pagos_dict = {}
        for r in all_rows:
            num = r.get("orden_numero")
            if num not in pagos_dict:
                pagos_dict[num] = {
                    "orden_numero": num,
                    "total_pago": 0,
                    "proyecto": r.get("proyecto")
                }
            try:
                monto = int(round(float(r.get("costo_final_con_iva") or 0)))
            except:
                monto = 0
            pagos_dict[num]["total_pago"] += monto
        
        print(f"✅ Órdenes únicas después de agrupar: {len(pagos_dict)}")
        
        # Obtener fechas de pago
        if prefetch and 'fechas_de_pagos_op' in prefetch:
            fechas_data = prefetch.get('fechas_de_pagos_op') or []
        else:
            page_size = 1000
            off = 0
            fechas_data = []
            while True:
                batch = supabase.table("fechas_de_pagos_op").select("orden_numero, fecha_pago").range(off, off + page_size - 1).execute().data or []
                if not batch:
                    break
                fechas_data.extend(batch)
                off += page_size
        
        # Construir mapa con claves string e int (IGUAL QUE PAGOS.PY)
        fecha_map = {}
        for row in fechas_data:
            k = row.get("orden_numero")
            v = row.get("fecha_pago")
            if k is None:
                continue
            fecha_map[str(k)] = v
            try:
                fecha_map[int(k)] = v
            except:
                pass
        
        # Obtener abonos
        if prefetch and 'abonos_op' in prefetch:
            abonos_data = prefetch.get('abonos_op') or []
        else:
            abonos_data = supabase.table("abonos_op").select("orden_numero, monto_abono").execute().data or []
        
        # Construir mapa de abonos (IGUAL QUE PAGOS.PY)
        abonos_map = {}
        for ab in abonos_data:
            num = ab.get("orden_numero")
            try:
                monto = int(round(float(ab.get("monto_abono") or 0)))
            except:
                monto = 0
            if num is None:
                continue
            try:
                num_int = int(num)
                abonos_map[num_int] = abonos_map.get(num_int, 0) + monto
            except:
                abonos_map[num] = abonos_map.get(num, 0) + monto
        
        # Contadores (IGUAL QUE PAGOS.PY)
        total_ordenes = len(pagos_dict)
        pagadas = 0
        pendientes = 0
        con_abonos = 0
        total_pendiente = 0.0
        total_saldo_abonos = 0.0
        
        # Recorrer órdenes y calcular (EXACTAMENTE IGUAL QUE PAGOS.PY)
        for num, pago in pagos_dict.items():
            total_abonado = abonos_map.get(num, 0)
            total_pago = pago["total_pago"]
            fecha_pago = fecha_map.get(num)
            
            # PRIMERO: Si tiene abonos Y NO tiene fecha_pago, calcular saldo y sumar
            if total_abonado > 0 and not fecha_pago:
                con_abonos += 1
                saldo = max(0, total_pago - total_abonado)
                total_saldo_abonos += saldo
            
            # SEGUNDO: Calcular estado para contadores (pagado vs pendiente)
            estado = calcular_estado_pago(fecha_pago, total_abonado, total_pago)
            
            if estado == "pagado":
                pagadas += 1
            elif estado == "pendiente":
                # Pendiente sin abonos - sumar el total completo a "Pendientes"
                pendientes += 1
                total_pendiente += total_pago
        
        # Total general (IGUAL QUE PAGOS.PY)
        total_general = total_pendiente + total_saldo_abonos
        
        # DEBUG: Log para verificar cálculos
        print(f"🔍 DEBUG Dashboard KPIs:")
        print(f"   Total órdenes únicas: {total_ordenes}")
        print(f"   Pagadas: {pagadas}")
        print(f"   Pendientes (sin abonos): {pendientes} → ${total_pendiente:,.0f}")
        print(f"   Con abonos: {con_abonos} → Saldo: ${total_saldo_abonos:,.0f}")
        print(f"   TOTAL GENERAL: ${total_general:,.0f}")
        
        # 3. DOCUMENTOS PENDIENTES
        # Facturas sin registrar (OP sin factura con saldo pendiente)
        facturas_pendientes = 0
        
        # Crear mapa de facturas desde ordenes_pago_raw
        factura_map = {}
        for r in all_rows:
            num = r.get("orden_numero")
            fac = r.get("factura")
            if num and fac and num not in factura_map:
                factura_map[num] = fac
        
        for num, pago in pagos_dict.items():
            total_pago = pago["total_pago"]
            total_abonado = abonos_map.get(num, 0)
            fecha_pago = fecha_map.get(num)
            
            if not fecha_pago:  # No está pagado
                saldo = max(0, total_pago - total_abonado)
                if saldo > 0 and not factura_map.get(num):
                    facturas_pendientes += 1
        
        # Órdenes sin recepcionar (>15 días)
        if prefetch and 'orden_de_compra' in prefetch:
            ordenes = prefetch.get('orden_de_compra') or []
        else:
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
        
        # Documentos pendientes: TODOS los pagos sin fecha_pago y con saldo > 0
        documentos_pendientes = 0
        documentos_con_abonos = 0
        pagos_vencidos = 0
        fecha_hoy = datetime.now()
        
        # Crear map de vencimientos desde ordenes_pago_raw
        vencimiento_map = {}
        for r in all_rows:
            num = r.get("orden_numero")
            venc = r.get("vencimiento")
            if num and venc and num not in vencimiento_map:
                vencimiento_map[num] = venc
        
        for num, pago in pagos_dict.items():
            total_pago = pago["total_pago"]
            total_abonado = abonos_map.get(num, 0)
            fecha_pago = fecha_map.get(num)
            vencimiento = vencimiento_map.get(num)
            
            # Si NO tiene fecha de pago y tiene saldo pendiente
            if not fecha_pago:
                saldo = max(0, total_pago - total_abonado)
                if saldo > 0:
                    documentos_pendientes += 1
                    
                    # Clasificar si tiene abonos
                    if total_abonado > 0:
                        documentos_con_abonos += 1
                    
                    # Verificar si está vencido
                    if vencimiento:
                        try:
                            fecha_venc = datetime.fromisoformat(vencimiento.replace('Z', '+00:00'))
                            if fecha_venc < fecha_hoy:
                                pagos_vencidos += 1
                        except:
                            pass
        
        print(f"📊 DOCUMENTOS PENDIENTES:")
        print(f"  • Total documentos pendientes: {documentos_pendientes}")
        print(f"  • Documentos con abonos: {documentos_con_abonos}")
        print(f"  • Pagos vencidos: {pagos_vencidos}")
        
        # 4. MÉTRICAS OPERACIONALES DEL MES ACTUAL
        fecha_inicio_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # OC del mes
        oc_mes_actual = 0
        monto_oc_mes = 0
        for oc in ordenes:
            fecha_str = oc.get('fecha_emision') or oc.get('fecha')
            if fecha_str:
                try:
                    # Intentar varios formatos de fecha
                    if 'T' in fecha_str:  # ISO format
                        fecha = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                    else:  # formato DD/MM/YYYY o similar
                        from dateutil import parser
                        fecha = parser.parse(fecha_str)
                    
                    # Comparar sin timezone para evitar problemas
                    if fecha.replace(tzinfo=None) >= fecha_inicio_mes:
                        oc_mes_actual += 1
                        monto_oc_mes += float(oc.get('monto_total', 0) or 0)
                except Exception as e:
                    # Si falla el parsing, intentar formato simple
                    try:
                        from datetime import datetime as dt
                        # Intenta DD-MM-YYYY
                        fecha = dt.strptime(fecha_str[:10], '%d-%m-%Y')
                        if fecha >= fecha_inicio_mes:
                            oc_mes_actual += 1
                            monto_oc_mes += float(oc.get('monto_total', 0) or 0)
                    except:
                        pass
        
        # Recepciones del mes (ingresos)
        if prefetch and 'ingresos' in prefetch:
            ingresos = prefetch.get('ingresos') or []
        else:
            response_ingresos = supabase.table('ingresos').select('*').execute()
            ingresos = response_ingresos.data if response_ingresos.data else []
        
        recepciones_mes = 0
        for ingreso in ingresos:
            fecha_str = ingreso.get('fecha_recepcion')
            if fecha_str:
                try:
                    if 'T' in fecha_str:
                        fecha = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                    else:
                        from dateutil import parser
                        fecha = parser.parse(fecha_str)
                    
                    if fecha.replace(tzinfo=None) >= fecha_inicio_mes:
                        recepciones_mes += 1
                except:
                    pass
        
        # Pagos del mes
        if prefetch and 'fechas_de_pagos_op' in prefetch:
            pagos = prefetch.get('fechas_de_pagos_op') or []
        else:
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
            # Nuevos campos separados (IGUAL QUE PAGOS.PY)
            "monto_pendiente": round(total_pendiente, 2),
            "saldo_abonos": round(total_saldo_abonos, 2),
            "total_general": round(total_general, 2),
            "pendientes": pendientes,
            "con_abonos": con_abonos,
            "pagadas": pagadas,
            "total_ordenes": total_ordenes,
            # Campos legacy (por compatibilidad)
            "deuda_total": round(total_general, 2),
            "cantidad_pendientes": pendientes + con_abonos,
            "documentos_pendientes": documentos_pendientes,
            "documentos_con_abonos": documentos_con_abonos,
            "facturas_pendientes": 0,  # No se muestra
            "oc_antiguas": 0,  # No se muestra
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


def obtener_top_proveedores_deuda(prefetch=None):
    """
    Top 5 proveedores con mayor deuda
    Usa la MISMA LÓGICA que pagos.py para calcular saldo real
    """
    try:
        # Obtener órdenes de pago
        if prefetch and 'orden_de_pago' in prefetch:
            ordenes_pago_raw = prefetch.get('orden_de_pago') or []
        else:
            response = supabase.table('orden_de_pago').select('*').execute()
            ordenes_pago_raw = response.data if response.data else []
        
        # Obtener fechas de pago
        if prefetch and 'fechas_de_pagos_op' in prefetch:
            fechas_pago = prefetch.get('fechas_de_pagos_op') or []
        else:
            response_fechas = supabase.table('fechas_de_pagos_op').select('*').execute()
            fechas_pago = response_fechas.data if response_fechas.data else []
        
        # Obtener abonos
        if prefetch and 'abonos_op' in prefetch:
            abonos_data = prefetch.get('abonos_op') or []
        else:
            response_abonos = supabase.table('abonos_op').select('*').execute()
            abonos_data = response_abonos.data if response_abonos.data else []
        
        # Crear maps de fechas y abonos (IGUAL QUE PAGOS.PY)
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
        
        abonos_map = {}
        for ab in abonos_data:
            num = ab.get("orden_numero")
            try:
                monto = int(round(float(ab.get("monto_abono") or 0)))
            except:
                monto = 0
            if num is None:
                continue
            try:
                num_int = int(num)
                abonos_map[num_int] = abonos_map.get(num_int, 0) + monto
            except:
                abonos_map[num] = abonos_map.get(num, 0) + monto
        
        # Agrupar por orden_numero primero
        pagos_dict = {}
        for r in ordenes_pago_raw:
            num = r.get("orden_numero")
            prov = r.get("proveedor_nombre", "Sin Proveedor")
            if num not in pagos_dict:
                pagos_dict[num] = {
                    "orden_numero": num,
                    "proveedor": prov,
                    "total_pago": 0
                }
            try:
                monto = int(round(float(r.get("costo_final_con_iva") or 0)))
            except:
                monto = 0
            pagos_dict[num]["total_pago"] += monto
        
        # Agrupar por proveedor y calcular deuda real
        deuda_por_proveedor = {}
        
        for num, pago in pagos_dict.items():
            proveedor = pago["proveedor"]
            total_pago = pago["total_pago"]
            total_abonado = abonos_map.get(num, 0)
            fecha_pago = fecha_map.get(num)
            
            # Calcular saldo REAL (solo si no está pagado)
            if not fecha_pago:
                saldo = max(0, total_pago - total_abonado)
                
                if saldo > 0:  # Solo contar si tiene saldo pendiente
                    if proveedor not in deuda_por_proveedor:
                        deuda_por_proveedor[proveedor] = {
                            'proveedor': proveedor,
                            'deuda': 0,
                            'num_op': 0
                        }
                    
                    deuda_por_proveedor[proveedor]['deuda'] += saldo
                    deuda_por_proveedor[proveedor]['num_op'] += 1
        
        # Ordenar todos los proveedores por deuda (no limitar a top 5)
        top_proveedores = sorted(
            deuda_por_proveedor.values(),
            key=lambda x: x['deuda'],
            reverse=True
        )
        
        # Redondear montos
        for prov in top_proveedores:
            prov['deuda'] = round(prov['deuda'], 2)
        
        return top_proveedores
    except Exception as e:
        print(f"Error en obtener_top_proveedores_deuda: {str(e)}")
        return []


def obtener_top_proyectos_criticos(prefetch=None):
    """
    Top 5 proyectos con mayor deuda y situación presupuestaria crítica
    """
    try:
        # Obtener órdenes de pago
        if prefetch and 'orden_de_pago' in prefetch:
            ordenes_pago = prefetch.get('orden_de_pago') or []
        else:
            response_op = supabase.table('orden_de_pago').select('*').execute()
            ordenes_pago = response_op.data if response_op.data else []

        # Obtener presupuestos
        if prefetch and 'presupuesto' in prefetch:
            presupuestos = prefetch.get('presupuesto') or []
        else:
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
        
        # Agrupar deuda y monto total por proyecto
        deuda_por_proyecto = {}
        
        for op in ordenes_pago:
            proyecto_id = op.get('proyecto_id')
            proyecto_nombre = op.get('proyecto_nombre', 'Sin Proyecto')
            monto = float(op.get('monto_total', 0) or 0)
            
            # Inicializar proyecto si no existe
            if proyecto_id not in deuda_por_proyecto:
                deuda_por_proyecto[proyecto_id] = {
                    'proyecto_id': proyecto_id,
                    'proyecto': proyecto_nombre,
                    'monto_total': 0,  # Nuevo campo: suma de todas las OP
                    'deuda': 0,  # Solo OP pendientes
                    'num_op': 0,
                    'saldo_presupuesto': 0
                }
            
            # Sumar monto total (todas las OP)
            deuda_por_proyecto[proyecto_id]['monto_total'] += monto
            
            # Sumar deuda (solo OP pendientes)
            if not op.get('pagado', False):
                deuda_por_proyecto[proyecto_id]['deuda'] += monto
                deuda_por_proyecto[proyecto_id]['num_op'] += 1
        
        # Agregar información presupuestaria y filtrar proyectos con deuda
        proyectos_con_deuda = {}
        for proyecto_id, data in deuda_por_proyecto.items():
            # Solo incluir proyectos que tengan deuda pendiente
            if data['deuda'] > 0:
                if proyecto_id in ppto_por_proyecto:
                    data['saldo_presupuesto'] = ppto_por_proyecto[proyecto_id]['saldo']
                
                # Determinar estado
                if data['saldo_presupuesto'] < 0:
                    data['estado'] = 'riesgo'
                elif data['saldo_presupuesto'] < data['deuda'] * 0.2:  # Menos del 20% de margen
                    data['estado'] = 'alerta'
                else:
                    data['estado'] = 'ok'
                
                proyectos_con_deuda[proyecto_id] = data
        
        # Ordenar por deuda y tomar top 5
        top_proyectos = sorted(
            proyectos_con_deuda.values(),
            key=lambda x: x['deuda'],
            reverse=True
        )[:5]
        
        # Redondear montos
        for proy in top_proyectos:
            proy['monto_total'] = round(proy['monto_total'], 2)
            proy['deuda'] = round(proy['deuda'], 2)
            proy['saldo_presupuesto'] = round(proy['saldo_presupuesto'], 2)
        
        return top_proyectos
    except Exception as e:
        print(f"Error en obtener_top_proyectos_criticos: {str(e)}")
        return []


def obtener_oc_sin_recepcionar(prefetch=None):
    """
    Órdenes de compra sin recepcionar (>15 días)
    """
    try:
        if prefetch and 'orden_de_compra' in prefetch:
            ordenes = prefetch.get('orden_de_compra') or []
        else:
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


def obtener_evolucion_deuda(prefetch=None):
    """
    Evolución de la deuda en los últimos 6 meses
    Calcula el saldo pendiente REAL al final de cada mes
    """
    try:
        # Obtener datos necesarios
        if prefetch and 'orden_de_pago' in prefetch:
            ordenes_pago_raw = prefetch.get('orden_de_pago') or []
        else:
            response = supabase.table('orden_de_pago').select('*').execute()
            ordenes_pago_raw = response.data if response.data else []
        
        if prefetch and 'fechas_de_pagos_op' in prefetch:
            fechas_pago = prefetch.get('fechas_de_pagos_op') or []
        else:
            response_fechas = supabase.table('fechas_de_pagos_op').select('*').execute()
            fechas_pago = response_fechas.data if response_fechas.data else []
        
        if prefetch and 'abonos_op' in prefetch:
            abonos_data = prefetch.get('abonos_op') or []
        else:
            response_abonos = supabase.table('abonos_op').select('*').execute()
            abonos_data = response_abonos.data if response_abonos.data else []
        
        # Crear maps (IGUAL QUE PAGOS.PY)
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
        
        abonos_map = {}
        for ab in abonos_data:
            num = ab.get("orden_numero")
            try:
                monto = int(round(float(ab.get("monto_abono") or 0)))
            except:
                monto = 0
            if num is None:
                continue
            try:
                num_int = int(num)
                abonos_map[num_int] = abonos_map.get(num_int, 0) + monto
            except:
                abonos_map[num] = abonos_map.get(num, 0) + monto
        
        # Agrupar órdenes por número
        pagos_dict = {}
        for r in ordenes_pago_raw:
            num = r.get("orden_numero")
            fecha_creacion = r.get("fecha_creacion")
            if num not in pagos_dict:
                pagos_dict[num] = {
                    "orden_numero": num,
                    "total_pago": 0,
                    "fecha_creacion": fecha_creacion
                }
            try:
                monto = int(round(float(r.get("costo_final_con_iva") or 0)))
            except:
                monto = 0
            pagos_dict[num]["total_pago"] += monto
        
        # Calcular deuda por mes (últimos 6 meses)
        evolucion = []
        fecha_actual = datetime.now()
        
        meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                         'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        
        for i in range(5, -1, -1):  # 6 meses atrás hasta hoy
            # Calcular último día del mes
            if fecha_actual.month - i > 0:
                mes = fecha_actual.month - i
                anio = fecha_actual.year
            else:
                mes = 12 + (fecha_actual.month - i)
                anio = fecha_actual.year - 1
            
            # Último día del mes a las 23:59:59
            if mes == 12:
                fecha_corte = datetime(anio, mes, 31, 23, 59, 59)
            elif mes in [1, 3, 5, 7, 8, 10]:
                fecha_corte = datetime(anio, mes, 31, 23, 59, 59)
            elif mes in [4, 6, 9, 11]:
                fecha_corte = datetime(anio, mes, 30, 23, 59, 59)
            else:  # Febrero
                fecha_corte = datetime(anio, mes, 28, 23, 59, 59)
            
            # Calcular deuda pendiente a esa fecha
            deuda_mes = 0
            
            for num, pago in pagos_dict.items():
                # Solo contar órdenes creadas antes del corte
                if pago.get('fecha_creacion'):
                    try:
                        fecha_creacion = datetime.fromisoformat(pago['fecha_creacion'].replace('Z', '+00:00'))
                        
                        if fecha_creacion <= fecha_corte:
                            # Verificar si estaba pagada a esa fecha
                            fecha_pago_str = fecha_map.get(num)
                            estaba_pagada = False
                            
                            if fecha_pago_str:
                                try:
                                    fecha_pago = datetime.fromisoformat(fecha_pago_str.replace('Z', '+00:00'))
                                    if fecha_pago <= fecha_corte:
                                        estaba_pagada = True
                                except:
                                    pass
                            
                            # Si no estaba pagada, sumar al saldo
                            if not estaba_pagada:
                                total_pago = pago["total_pago"]
                                total_abonado = abonos_map.get(num, 0)
                                saldo = max(0, total_pago - total_abonado)
                                deuda_mes += saldo
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


def obtener_distribucion_deuda_proveedor(prefetch=None):
    """
    Distribución de deuda por proveedor (para gráfico pie)
    """
    try:
        top_proveedores = obtener_top_proveedores_deuda(prefetch=prefetch)
        
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


def obtener_ejecucion_presupuestaria(prefetch=None):
    """
    Ejecución presupuestaria por proyecto (para gráfico barras)
    """
    try:
        if prefetch and 'presupuesto' in prefetch:
            presupuestos = prefetch.get('presupuesto') or []
        else:
            response = supabase.table('presupuesto').select('*').execute()
            presupuestos = response.data if response.data else []

        # Obtener nombres de proyectos
        if prefetch and 'proyectos' in prefetch:
            proyectos = prefetch.get('proyectos') or []
        else:
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