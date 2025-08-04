# Place after bp_pagos definition

"""
LÓGICA DE PAGOS - DOS MÉTODOS:

MÉTODO A - PAGO DIRECTO:
- Usuario asigna fecha de pago directamente
- Representa pago completo (saldo = 0)
- No requiere abonos previos
- Independiente del sistema de abonos

MÉTODO B - PAGO POR ABONOS:
- Usuario registra abonos parciales
- Sistema suma abonos hasta completar total
- Cuando abonos = total → auto-asigna fecha de pago
- Si se elimina abono y saldo > 0 → se elimina fecha de pago automática

REGLAS DE CONVIVENCIA:
1. Pago directo (fecha) siempre tiene precedencia
2. Sistema de abonos solo gestiona fechas automáticas
3. No eliminar fechas de pago directo por cambios en abonos
4. Permitir ambos métodos sin interferencia
"""



from flask import (
    Blueprint, render_template, request,
    flash, redirect, url_for, current_app,
    send_file, jsonify
)
from datetime import date, datetime, timedelta
from flask_login import login_required
import io
from openpyxl import Workbook
from app.modules.usuarios import require_modulo, get_modulos_usuario
from app.utils.static_data import get_cached_proveedores, get_cached_proyectos_with_id
from utils.logger import registrar_log_actividad

bp_pagos = Blueprint(
    "pagos", __name__,
    template_folder="../templates"
)

@login_required
@bp_pagos.route('/abonos/<int:abono_id>', methods=['PUT'])
@require_modulo('pagos')
def editar_abono_op(abono_id):
    supabase = current_app.config["SUPABASE"]
    try:
        data = request.get_json() or {}
        monto = int(round(float(data.get("monto_abono") or 0)))
        fecha = data.get("fecha_abono")
        observacion = data.get("observacion")
        
        if monto <= 0:
            return jsonify(success=False, error="Monto debe ser mayor a cero"), 400
        
        # OPTIMIZACIÓN: Combinar consultas en una sola transacción
        # 1. Obtener orden_numero y total_pago en una consulta combinada
        res_abono = supabase.table("abonos_op").select("orden_numero").eq("id", abono_id).limit(1).execute()
        if not res_abono.data:
            return jsonify(success=False, error="No se encontró el abono."), 400
        orden_numero = res_abono.data[0]["orden_numero"]
        
        # 2. Obtener total_pago y suma de otros abonos en paralelo
        res_pago = supabase.table("orden_de_pago").select("costo_final_con_iva").eq("orden_numero", orden_numero).limit(1).execute()
        if not res_pago.data:
            return jsonify(success=False, error="No se encontró el total de la orden."), 400
        total_pago = int(round(float(res_pago.data[0].get("costo_final_con_iva") or 0)))
        
        # 3. Consultar otros abonos (excluyendo el que se está editando)
        res_otros_abonos = supabase.table("abonos_op").select("monto_abono").eq("orden_numero", orden_numero).neq("id", abono_id).execute()
        suma_otros_abonos = sum(int(round(float(a.get("monto_abono") or 0))) for a in (res_otros_abonos.data or []))
        
        # 4. Validar que suma de otros abonos + nuevo monto <= total_pago
        nueva_suma = suma_otros_abonos + monto
        if nueva_suma > total_pago:
            return jsonify(success=False, error=f"La suma de abonos ({nueva_suma}) supera el total de la orden ({total_pago})."), 400
        
        update_data = {"monto_abono": monto}
        if fecha:
            update_data["fecha_abono"] = fecha
        if observacion is not None:
            update_data["observacion"] = observacion
        
        res = supabase.table("abonos_op").update(update_data).eq("id", abono_id).execute()
        if hasattr(res, "error") and res.error:
            return jsonify(success=False, error=str(res.error)), 500
        
        # 5. Verificar si después de la edición se debe mantener o eliminar la fecha de pago
        # SOLO eliminar fecha de pago si hay saldo pendiente en el sistema de abonos
        if nueva_suma == total_pago:
            # Si completa el total, asegurar que tenga fecha de pago (usar la fecha del abono editado)
            supabase.table("fechas_de_pagos_op").upsert({"orden_numero": orden_numero, "fecha_pago": fecha or date.today().isoformat()}, on_conflict=["orden_numero"]).execute()
        elif nueva_suma > 0:
            # Si hay abonos pero no completan el total, eliminar fecha de pago automática
            # PERO solo si la fecha fue puesta automáticamente por el sistema de abonos
            # No eliminar fechas puestas manualmente por pago directo
            pass  # Mantenemos la fecha existente si fue puesta manualmente
        else:
            # Si no hay abonos, eliminar la fecha de pago automática
            supabase.table("fechas_de_pagos_op").delete().eq("orden_numero", orden_numero).execute()
        
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

def get_pagos(filtros=None):
    supabase = current_app.config["SUPABASE"]
    
    # OPTIMIZACIÓN: Solo traer las columnas necesarias
    page_size = 1000  
    offset = 0
    all_rows = []
    
    try:
        while True:
            batch = supabase \
                .table("orden_de_pago") \
                .select("orden_numero, fecha, proveedor, proveedor_nombre, detalle_compra, factura, costo_final_con_iva, proyecto, orden_compra, condicion_pago, vencimiento, fecha_factura") \
                .order("orden_numero") \
                .range(offset, offset + page_size - 1) \
                .execute() \
                .data or []

            all_rows.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
    except Exception as e:
        print(f"[ERROR] Consulta orden_de_pago: {e}")
        return []



    # Aplicar filtros si corresponde (aquí puedes adaptar según tus filtros)
    if filtros:
        if filtros.get("proveedor"):
            all_rows = [r for r in all_rows if r["proveedor_nombre"] == filtros["proveedor"]]

    # Agrupar por orden_numero único, sumar montos, y tomar los demás datos del primer registro
    pagos = {}
    for r in all_rows:
        try:
            num = int(r["orden_numero"])
        except (ValueError, TypeError):
            continue  # Si no se puede convertir, omitir
        if num not in pagos:
            pagos[num] = {
                "orden_numero": num,
                "fecha": r["fecha"],
                "proveedor": r.get("proveedor"),  # ID del proveedor
                "proveedor_nombre": r["proveedor_nombre"],
                "detalle_compra": r["detalle_compra"],
                "factura": r["factura"],
                "total_pago": 0.0,
                "proyecto": r["proyecto"],
                "orden_compra": r["orden_compra"],
                "condicion_pago": r["condicion_pago"],
                "vencimiento": r["vencimiento"],
                "fecha_factura": r["fecha_factura"],
                "fecha_pago": None
            }
        pagos[num]["total_pago"] += float(r.get("costo_final_con_iva") or 0)

    # Ordenar de mayor a menor por orden_numero
    pagos_ordenados = [pagos[k] for k in sorted(pagos.keys(), reverse=True)]

    # Obtener todos los orden_compra únicos de los pagos
    ordenes_compra_unicas = set(r["orden_compra"] for r in pagos_ordenados if r.get("orden_compra"))
    # Consultar items únicos para cada orden_compra
    items_por_orden = {}
    if ordenes_compra_unicas:
        batch_size = 100
        ordenes_list = list(ordenes_compra_unicas)
        for i in range(0, len(ordenes_list), batch_size):
            batch_ordenes = ordenes_list[i:i+batch_size]
            batch_items = supabase.table("orden_de_compra").select("orden_compra,item").in_("orden_compra", batch_ordenes).execute().data or []
            for oc in batch_ordenes:
                items = set(row["item"] for row in batch_items if row["orden_compra"] == oc and row.get("item"))
                items_por_orden[oc] = ", ".join(sorted(items)) if items else ""
    # Agregar campo 'item' a cada pago
    for data in pagos_ordenados:
        oc = data.get("orden_compra")
        data["item"] = items_por_orden.get(oc, "")
    # Fechas de pago existentes

    # OPTIMIZACIÓN: Traer fechas de pago en una sola consulta eficiente
    try:
        fechas_data = supabase.table("fechas_de_pagos_op").select("orden_numero, fecha_pago").execute().data or []
        fecha_map = {str(row["orden_numero"]): row["fecha_pago"] for row in fechas_data}
    except Exception as e:
        print(f"[ERROR] Consulta fechas de pago: {e}")
        fecha_map = {}
    for data in pagos_ordenados:
        data["fecha_pago"] = fecha_map.get(str(data["orden_numero"]))

    # Cuentas corrientes de proveedores - usar datos cacheados
    provs = get_cached_proveedores()
    cuenta_map = {p["nombre"]: p["cuenta"] for p in provs}
    for data in pagos_ordenados:
        data["cuenta"] = cuenta_map.get(data["proveedor_nombre"], "")

    # Nombres de proyectos - usar datos cacheados
    projs = get_cached_proyectos_with_id()
    proyecto_map = {pr["id"]: pr["proyecto"] for pr in projs}
    for data in pagos_ordenados:
        proj_id = data.get("proyecto")
        data["proyecto"] = proyecto_map.get(proj_id, proj_id)

    # OPTIMIZACIÓN: Traer abonos en una sola consulta
    try:
        abonos_data = supabase.table("abonos_op").select("orden_numero, monto_abono").execute().data or []
        abonos_map = {}
        for ab in abonos_data:
            num = ab.get("orden_numero")
            if num is not None:
                try:
                    monto = float(ab.get("monto_abono") or 0)
                    abonos_map[num] = abonos_map.get(num, 0) + monto
                except (ValueError, TypeError):
                    continue
    except Exception as e:
        print(f"[ERROR] Consulta abonos: {e}")
        abonos_map = {}

    # Calcular saldo pendiente para cada orden
    for data in pagos_ordenados:
        num = data["orden_numero"]
        total_abonado = abonos_map.get(num, 0)
        data["total_abonado"] = total_abonado
        
        # Si existe fecha_pago → saldo = 0, sino saldo = total - abonos
        data["saldo_pendiente"] = 0 if data.get("fecha_pago") else max(0, data["total_pago"] - total_abonado)

    return pagos_ordenados

@login_required
@bp_pagos.route("/pagos", methods=["GET"])
@require_modulo('pagos')
def list_pagos():
    # Bloquear acceso a usuarios sin el módulo 'pagos'
    modulos_usuario = [m.strip().lower() for m in get_modulos_usuario()]
    if 'pagos' not in modulos_usuario:
        flash('No tienes permiso para acceder a esta sección.', 'danger')
        return render_template('sin_permisos.html')

    # Recoger filtros de la URL
    filtros = {}
    proveedor = request.args.get("proveedor", "").strip()
    proyecto = request.args.get("proyecto", "").strip()
    estado = request.args.get("estado", "").strip()  # pagado, pendiente, vencido
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()

    if proveedor:
        filtros["proveedor"] = proveedor
    if proyecto:
        filtros["proyecto"] = proyecto
    if estado:
        filtros["estado"] = estado
    if fecha_desde:
        filtros["fecha_desde"] = fecha_desde
    if fecha_hasta:
        filtros["fecha_hasta"] = fecha_hasta

    pagos = get_pagos(filtros)

    # Calcular el total pendiente como la suma de la columna saldo_pendiente
    total_pendiente = sum(p.get("saldo_pendiente", 0) for p in pagos)

    # Datos adicionales para el template
    proveedores_unicos = sorted(set(p["proveedor_nombre"] for p in pagos))
    proyectos_unicos = sorted(set(p["proyecto"] for p in pagos))

    # Calcular fecha máxima para el input de fecha (hoy + 7 días)
    fecha_maxima = (date.today() + timedelta(days=7)).isoformat()

    # Permisos: solo puede editar si tiene el módulo 'pagos'
    puede_editar = 'pagos' in modulos_usuario

    return render_template(
        "pagos.html",
        pagos=pagos,
        fecha_maxima=fecha_maxima,
        proveedores_unicos=proveedores_unicos,
        proyectos_unicos=proyectos_unicos,
        filtros_activos=filtros,
        total_pendiente=total_pendiente,
        puede_editar=puede_editar,
        date=date
    )

@login_required
@bp_pagos.route("/pagos/update", methods=["POST"])
@require_modulo('pagos')
def update_pagos():
    supabase = current_app.config["SUPABASE"]
    nums = request.form.getlist("orden_numero[]")
    fechas = request.form.getlist("fecha_pago[]")
    
    # Protección contra envío vacío o duplicado
    if not nums or len(nums) == 0:
        flash("No se enviaron datos para actualizar.", "warning")
        return redirect(url_for("pagos.list_pagos"))
    
    any_error = False
    upserts = []
    deletes = []
    ordenes_con_abonos = []  # Para acumular órdenes que no se pueden borrar
    
    # OPTIMIZACIÓN: Consultar fechas actuales una sola vez para todas las órdenes
    fechas_actuales = {}
    if nums:
        try:
            ordenes_numericas = [int(num) for num in nums]
            res_fechas = supabase.table("fechas_de_pagos_op").select("orden_numero, fecha_pago").in_("orden_numero", ordenes_numericas).execute()
            fechas_actuales = {row["orden_numero"]: row["fecha_pago"] for row in (res_fechas.data or [])}
        except Exception as e:
            print(f"[ERROR] Consulta fechas actuales: {e}")
            fechas_actuales = {}

    # OPTIMIZACIÓN: Consultar abonos una sola vez para todas las órdenes
    abonos_por_orden = {}
    if nums:
        try:
            ordenes_numericas = [int(num) for num in nums]
            # Consulta única para todas las órdenes (más eficiente)
            res_abonos = supabase.table("abonos_op").select("orden_numero, monto_abono").in_("orden_numero", ordenes_numericas).execute()
            
            for abono in (res_abonos.data or []):
                orden_num = abono.get("orden_numero")
                monto = int(round(float(abono.get("monto_abono") or 0)))
                abonos_por_orden[orden_num] = abonos_por_orden.get(orden_num, 0) + monto
                
        except Exception as e:
            print(f"[ERROR] Consulta abonos: {e}")
            abonos_por_orden = {}

    for i, num in enumerate(nums):
        fpago = fechas[i].strip() if i < len(fechas) else ""
        orden_numero = int(num)
        
        # Obtener la fecha actual de la BD (precargada)
        fecha_actual = fechas_actuales.get(orden_numero)
        
        # Obtener suma de abonos del diccionario precalculado
        suma_abonos = abonos_por_orden.get(orden_numero, 0)
        
        if fpago:
            # PAGO DIRECTO: Permitir asignar fecha independientemente de abonos
            try:
                d = datetime.strptime(fpago, "%Y-%m-%d").date()
            except ValueError:
                flash(f"Fecha inválida para OP {num}", "danger")
                any_error = True
                continue
            if d > date.today() + timedelta(days=7):
                flash(f"Fecha de pago muy futura para OP {num}", "danger")
                any_error = True
                continue
            
            # Solo actualizar si la fecha es diferente a la actual
            if fecha_actual != fpago:
                upserts.append({"orden_numero": orden_numero, "fecha_pago": fpago})
        else:
            # Si el campo está vacío, verificar si realmente se está ELIMINANDO una fecha existente
            if fecha_actual is not None:  # Solo si había una fecha antes
                if suma_abonos > 0:
                    # CRÍTICO: Solo mostrar mensaje si realmente se está eliminando una fecha de orden con abonos
                    ordenes_con_abonos.append(num)
                    any_error = True
                    continue
                else:
                    # Si no hay abonos, permitir eliminar la fecha libremente
                    deletes.append(orden_numero)
            # Si no había fecha antes y sigue sin fecha, no hacer nada

    # Upsert masivo si hay datos válidos
    if upserts:
        supabase.table("fechas_de_pagos_op").upsert(upserts, on_conflict=["orden_numero"]).execute()
        # Log de actualización de fechas de pago
        registrar_log_actividad(
            accion="update",
            tabla_afectada="fechas_de_pagos_op",
            descripcion=f"Actualizó fechas de pago para OPs: {[u['orden_numero'] for u in upserts]}",
            datos_despues=upserts
        )

    # Eliminar filas completas para las fechas borradas en una sola consulta
    if deletes:
        supabase.table("fechas_de_pagos_op").delete().in_("orden_numero", deletes).execute()
        # Log de eliminación de fechas de pago
        registrar_log_actividad(
            accion="delete",
            tabla_afectada="fechas_de_pagos_op",
            descripcion=f"Eliminó fechas de pago para OPs: {deletes}",
            datos_antes=deletes
        )

    # Mostrar mensaje ÚNICO para órdenes con abonos que no se pueden borrar
    if ordenes_con_abonos:
        if len(ordenes_con_abonos) == 1:
            flash(f"No puedes borrar la fecha de pago de la OP {ordenes_con_abonos[0]} porque tiene abonos registrados. Debes borrar los abonos primero.", "danger")
        else:
            flash(f"No puedes borrar las fechas de pago de las OPs {', '.join(ordenes_con_abonos)} porque tienen abonos registrados. Debes borrar los abonos primero.", "danger")

    if not any_error:
        flash("Fechas de pago actualizadas con éxito", "success")
    return redirect(url_for("pagos.list_pagos"))

@login_required
@bp_pagos.route('/pagos/export', methods=['GET'])
@require_modulo('pagos')
def export_pagos():
    # Toma los mismos filtros de la vista, si tienes más, agrégalos aquí
    filtros = {}
    proveedor = request.args.get("proveedor")
    if proveedor:
        filtros["proveedor"] = proveedor
    pagos = get_pagos(filtros)

    # Forzar invalidación del cache de proveedores antes de obtener datos
    from app.utils.static_data import invalidate_static_cache
    invalidate_static_cache("proveedores")
    provs = get_cached_proveedores()
    
    # Imprimir info de debug en los logs del servidor
    print(f"[DEBUG EXPORT] Total proveedores cargados: {len(provs)}")
    print(f"[DEBUG EXPORT] Total pagos a exportar: {len(pagos)}")
    print(f"[DEBUG EXPORT] Proveedores con RUT: {len([p for p in provs if p.get('rut')])}")
    
    # Crear múltiples mapas para manejar diferentes tipos de ID
    rut_map = {}
    for p in provs:
        if p.get("id") is not None and p.get("rut"):
            # Agregar todas las variantes posibles del ID
            rut_map[p["id"]] = p["rut"]
            try:
                rut_map[int(p["id"])] = p["rut"]
            except (ValueError, TypeError):
                pass
            try:
                rut_map[str(p["id"])] = p["rut"]
            except (ValueError, TypeError):
                pass

    # Columnas del Excel: agregar RUT después de PROVEEDOR y nuevas columnas de abono/saldo
    headers = [
        "fecha", "orden_numero", "proveedor_nombre", "rut_proveedor", "detalle_compra",
        "factura", "total_pago", "total_abonado", "saldo_pendiente", "fecha_pago", "proyecto", "orden_compra",
        "item", "condicion_pago", "vencimiento", "fecha_factura"
    ]

    col_names = [
        "FECHA OP", "O.PAGO", "PROVEEDOR", "RUT PROVEEDOR", "DETALLE O.PAGO",
        "FACTURA ASOCIADA", "TOTAL PAGO", "ABONADO", "SALDO PENDIENTE", "FECHA DE PAGO", "PROYECTO",
        "O. DE COMPRA", "ITEM(S)", "CONDICIÓN DE PAGO",
        "VENCIMIENTO FAC.", "FECHA DE FAC."
    ]

    # Agregar rut_proveedor a cada pago usando el ID del proveedor
    pagos_con_rut = 0
    pagos_sin_rut = 0
    
    for data in pagos:
        proveedor_id = data.get("proveedor")
        rut_encontrado = ""
        
        if proveedor_id is not None:
            # Buscar RUT en el mapa usando el ID tal como viene
            rut_encontrado = rut_map.get(proveedor_id, "")
            
            if not rut_encontrado:
                # Si no se encuentra, intentar conversiones
                try:
                    rut_encontrado = rut_map.get(int(proveedor_id), "")
                except (ValueError, TypeError):
                    pass
                
                if not rut_encontrado:
                    try:
                        rut_encontrado = rut_map.get(str(proveedor_id), "")
                    except (ValueError, TypeError):
                        pass
        
        data["rut_proveedor"] = rut_encontrado
        
        if rut_encontrado:
            pagos_con_rut += 1
        else:
            pagos_sin_rut += 1
    
    print(f"[DEBUG EXPORT] Pagos con RUT asignado: {pagos_con_rut}")
    print(f"[DEBUG EXPORT] Pagos sin RUT: {pagos_sin_rut}")

    wb = Workbook()
    ws = wb.active
    ws.title = "Pagos"

    # Formateador de pesos chilenos
    def format_pesos(valor):
        try:
            valor = float(valor)
        except (ValueError, TypeError):
            return ""
        return "$ {:,}".format(int(round(valor))).replace(",", ".")

    # RESUMEN POR PROYECTO (tabla arriba)
    ws.append(["RESUMEN POR PROYECTO"])
    ws.append(["PROYECTO", "SALDO PENDIENTE"])
    resumen_proyectos = {}
    for row in pagos:
        proyecto = row.get("proyecto", "(Sin proyecto)")
        resumen_proyectos[proyecto] = resumen_proyectos.get(proyecto, 0) + row.get("saldo_pendiente", 0)
    for proyecto, saldo in resumen_proyectos.items():
        ws.append([str(proyecto), format_pesos(saldo)])
    ws.append(["TOTAL SALDO PENDIENTE", format_pesos(sum(row.get("saldo_pendiente", 0) for row in pagos))])
    ws.append([])

    # Escribir cabeceras bonitas y la tabla principal
    ws.append(col_names)
    for row in pagos:
        fila = []
        for h in headers:
            if h in ["total_pago", "total_abonado", "saldo_pendiente"]:
                fila.append(format_pesos(row.get(h, 0)))
            else:
                fila.append(row.get(h, ""))
        ws.append(fila)

    # Agregar total al final (columna TOTAL PAGO, ABONADO y SALDO PENDIENTE)
    ws.append([])
    ws.append([
        "", "", "", "", "TOTALES", "", 
        format_pesos(sum(row["total_pago"] for row in pagos)),
        format_pesos(sum(row.get("total_abonado", 0) for row in pagos)),
        format_pesos(sum(row.get("saldo_pendiente", 0) for row in pagos))
    ])

    # Log de exportación de pagos
    registrar_log_actividad(
        accion="export",
        tabla_afectada="pagos",
        descripcion=f"Exportó pagos a Excel. Filtros: {filtros}. Pagos con RUT: {pagos_con_rut}, sin RUT: {pagos_sin_rut}",
        datos_despues=f"{len(pagos)} pagos exportados"
    )

    # Guardar y descargar
    output_bytes = io.BytesIO()
    wb.save(output_bytes)
    output_bytes.seek(0)
    filename = f"pagos_{date.today().isoformat()}.xlsx"
    return send_file(
        output_bytes,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@login_required
@bp_pagos.route('/pagos/debug_ruts', methods=['GET'])
@require_modulo('pagos')
def debug_ruts():
    """Función de depuración para verificar los RUTs de proveedores"""
    from app.utils.static_data import invalidate_static_cache
    invalidate_static_cache("proveedores")
    
    # Obtener proveedores desde cache
    provs = get_cached_proveedores()
    
    # Obtener algunos pagos para verificar
    filtros = {}
    proveedor = request.args.get("proveedor")
    if proveedor:
        filtros["proveedor"] = proveedor
    pagos = get_pagos(filtros)
    
    # Crear mapas de debug
    rut_map = {p["id"]: p.get("rut", "") for p in provs}
    
    debug_info = {
        "total_proveedores": len(provs),
        "total_pagos": len(pagos),
        "proveedores_con_rut": len([p for p in provs if p.get("rut")]),
        "proveedores_sin_rut": len([p for p in provs if not p.get("rut")]),
        "muestras_proveedores": provs[:5],  # Primeros 5 proveedores
        "muestras_pagos": pagos[:3],  # Primeros 3 pagos
        "rut_map_muestra": dict(list(rut_map.items())[:10])  # Primeras 10 entradas del map
    }
    
    return jsonify(debug_info)

@login_required
@bp_pagos.route('/pagos/verificar_proveedores', methods=['GET'])
@require_modulo('pagos')
def verificar_proveedores():
    """Función para verificar la consistencia entre proveedores en pagos y tabla proveedores"""
    supabase = current_app.config["SUPABASE"]
    
    try:
        # Obtener todos los IDs de proveedores únicos de orden_de_pago
        res_pagos = supabase.table("orden_de_pago").select("proveedor").execute()
        ids_en_pagos = set(p.get("proveedor") for p in (res_pagos.data or []) if p.get("proveedor") is not None)
        
        # Obtener todos los proveedores de la tabla proveedores
        provs = get_cached_proveedores()
        ids_en_proveedores = set(p["id"] for p in provs if p.get("id") is not None)
        
        # Encontrar IDs que están en pagos pero no en proveedores
        ids_faltantes = ids_en_pagos - ids_en_proveedores
        
        # Encontrar proveedores sin RUT
        provs_sin_rut = [p for p in provs if not p.get("rut") or p.get("rut").strip() == ""]
        
        resultado = {
            "total_ids_en_pagos": len(ids_en_pagos),
            "total_proveedores": len(provs),
            "ids_faltantes": list(ids_faltantes),
            "count_ids_faltantes": len(ids_faltantes),
            "proveedores_sin_rut": len(provs_sin_rut),
            "muestras_sin_rut": provs_sin_rut[:5] if provs_sin_rut else []
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@login_required
@bp_pagos.route('/abonos/<int:orden_numero>', methods=['GET'])
@require_modulo('pagos')
def get_abonos_op(orden_numero):
    supabase = current_app.config["SUPABASE"]
    try:
        # Obtener solo abonos activos (sin historial para empezar limpio)
        res = supabase.table("abonos_op").select("id, orden_numero, monto_abono, fecha_abono, observacion, created_at").eq("orden_numero", orden_numero).order("fecha_abono", desc=False).execute()
        abonos = res.data if hasattr(res, "data") and res.data else []
        
        response = jsonify(success=True, abonos=abonos)
        # Headers anti-cache para evitar que el navegador cachee esta respuesta
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    except Exception as e:
        print(f"[ERROR] Consulta abonos_op para OP {orden_numero}: {e}")
        return jsonify(success=True, abonos=[])

@login_required
@bp_pagos.route('/abonos/<int:orden_numero>', methods=['POST'])
@require_modulo('pagos')
def registrar_abono_op(orden_numero):
    supabase = current_app.config["SUPABASE"]
    try:
        data = request.get_json() or {}
        monto = int(round(float(data.get("monto_abono") or 0)))
        fecha = data.get("fecha_abono")
        observacion = data.get("observacion")

        if monto <= 0:
            return jsonify(success=False, error="Monto debe ser mayor a cero"), 400
        if not fecha:
            return jsonify(success=False, error="Fecha requerida"), 400

        # 1. Consultar suma actual de abonos para la orden
        res_abonos = supabase.table("abonos_op").select("monto_abono").eq("orden_numero", orden_numero).execute()
        suma_abonos = sum(int(round(float(a.get("monto_abono") or 0))) for a in (res_abonos.data or []))

        # 2. Consultar total_pago de la orden
        res_pago = supabase.table("orden_de_pago").select("costo_final_con_iva").eq("orden_numero", orden_numero).limit(1).execute()
        if not res_pago.data:
            return jsonify(success=False, error="No se encontró el total de la orden."), 400
        total_pago = int(round(float(res_pago.data[0].get("costo_final_con_iva") or 0)))

        # 3. Validar que suma actual + nuevo abono <= total_pago
        nueva_suma = suma_abonos + monto
        if nueva_suma > total_pago:
            return jsonify(success=False, error=f"La suma de abonos ({nueva_suma}) supera el total de la orden ({total_pago})."), 400

        abono = {
            "orden_numero": orden_numero,
            "monto_abono": monto,
            "fecha_abono": fecha,
            "observacion": observacion or None,
        }

        res = supabase.table("abonos_op").insert(abono).execute()
        if hasattr(res, "error") and res.error:
            return jsonify(success=False, error=str(res.error)), 500

        # Si la suma de abonos + monto es igual al total_pago, registrar fecha_pago automáticamente
        if nueva_suma == total_pago:
            supabase.table("fechas_de_pagos_op").upsert({"orden_numero": orden_numero, "fecha_pago": fecha}, on_conflict=["orden_numero"]).execute()
        # No eliminar fecha de pago aquí si nueva_suma < total_pago
        # porque puede existir una fecha de pago manual (pago directo) que no debe ser eliminada

        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# Endpoint DELETE para eliminar abonos (sin logging para evitar historial)
@login_required
@bp_pagos.route('/abonos/<int:abono_id>', methods=['DELETE'])
@require_modulo('pagos')
def eliminar_abono_op(abono_id):
    supabase = current_app.config["SUPABASE"]
    try:
        # OPTIMIZACIÓN: Obtener orden_numero antes de eliminar, luego verificar saldos
        res_abono = supabase.table("abonos_op").select("orden_numero").eq("id", abono_id).limit(1).execute()
        if not res_abono.data:
            return jsonify(success=False, error="No se encontró el abono."), 400
        orden_numero = res_abono.data[0]["orden_numero"]

        # Eliminar el abono
        res = supabase.table("abonos_op").delete().eq("id", abono_id).execute()
        if hasattr(res, "error") and res.error:
            return jsonify(success=False, error=str(res.error)), 500

        # Verificar suma restante y total en una sola operación
        res_abonos_restantes = supabase.table("abonos_op").select("monto_abono").eq("orden_numero", orden_numero).execute()
        suma_restante = sum(int(round(float(a.get("monto_abono") or 0))) for a in (res_abonos_restantes.data or []))
        
        # Solo consultar total_pago si es necesario para la lógica
        if suma_restante > 0:
            res_pago = supabase.table("orden_de_pago").select("costo_final_con_iva").eq("orden_numero", orden_numero).limit(1).execute()
            total_pago = int(round(float(res_pago.data[0].get("costo_final_con_iva") or 0))) if res_pago.data else 0
            
            # Mantener fecha si suma_restante == total_pago, eliminar si suma_restante < total_pago
            if suma_restante < total_pago:
                supabase.table("fechas_de_pagos_op").delete().eq("orden_numero", orden_numero).execute()
        else:
            # Si no quedan abonos, eliminar fecha de pago automática
            supabase.table("fechas_de_pagos_op").delete().eq("orden_numero", orden_numero).execute()

        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500