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



from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, send_file, jsonify
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

    # --- FUNCION AUXILIAR PARA SUMAR SALDO PENDIENTE POR PROYECTO ---
    def saldo_penproyecto(pagos):
        """
        Recibe una lista de pagos (diccionarios) y retorna un diccionario
        con el total de saldo pendiente agrupado por proyecto.
        """
        resultado = {}
        for pago in pagos:
            proyecto = pago.get("proyecto")
            saldo = pago.get("saldo_pendiente", 0)
            if proyecto:
                resultado[proyecto] = resultado.get(proyecto, 0) + saldo
        return resultado

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
                .select("orden_numero, fecha, proveedor, proveedor_nombre, detalle_compra, factura, costo_final_con_iva, proyecto, orden_compra, condicion_pago, vencimiento, fecha_factura, ingreso_id") \
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



    # Aplicar filtros si corresponde (adaptado para búsqueda parcial y número de orden)
    if filtros:
        # Filtro de búsqueda parcial (searchInput: proveedor, detalle, factura, proyecto, número de orden)
        search = filtros.get("proveedor", "").strip().lower()
        if search:
            all_rows = [r for r in all_rows if search in str(r.get("proveedor_nombre", "")).lower()
                        or search in str(r.get("detalle_compra", "")).lower()
                        or search in str(r.get("factura", "")).lower()
                        or search in str(r.get("proyecto", "")).lower()
                        or search in str(r.get("orden_numero", "")).lower()]

        # Filtro de proyecto exacto
        proyecto = filtros.get("proyecto", "").strip()
        if proyecto:
            all_rows = [r for r in all_rows if str(r.get("proyecto", "")) == proyecto]

        # Filtro de estado (pagado, pendiente, abono)
        estado = filtros.get("estado", "").strip()
        if estado:
            # Se filtra después de agrupar, ver más abajo
            pass

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
                "ingreso_id": r.get("ingreso_id"),  # Nueva columna para FAC. PAGO
                "fecha_pago": None
            }
        pagos[num]["total_pago"] += float(r.get("costo_final_con_iva") or 0)

    # Ordenar de mayor a menor por orden_numero
    pagos_ordenados = [pagos[k] for k in sorted(pagos.keys(), reverse=True)]

    # Filtro de estado (pagado, pendiente, abono) después de agrupar
    if filtros and filtros.get("estado"):
        estado = filtros["estado"]
        def estado_pago(p):
            if p["fecha_pago"]:
                return "pagado"
            elif p["total_abonado"] > 0 and p["saldo_pendiente"] > 0:
                return "abono"
            else:
                return "pendiente"
        pagos_ordenados = [p for p in pagos_ordenados if estado_pago(p) == estado]

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

    # OPTIMIZACIÓN: Traer fechas de pago con batch processing
    # Usar mismo patrón que las órdenes principales para evitar límites de Supabase
    try:
        fechas_data = []
        page_size = 1000
        offset = 0
        
        while True:
            batch = supabase.table("fechas_de_pagos_op").select("orden_numero, fecha_pago").range(offset, offset + page_size - 1).execute().data or []
            if not batch:
                break
            fechas_data.extend(batch)
            offset += page_size
        
        fecha_map = {str(row["orden_numero"]): row["fecha_pago"] for row in fechas_data}
    except Exception as e:
        print(f"[ERROR] Consulta fechas de pago: {e}")
        fecha_map = {}
    
    for data in pagos_ordenados:
        data["fecha_pago"] = fecha_map.get(str(data["orden_numero"]))

    # Cuentas corrientes de proveedores - usar datos cacheados
    provs = get_cached_proveedores()
    cuenta_map = {p["nombre"]: p["cuenta"] for p in provs}
    rut_map = {}
    for p in provs:
        if p.get("id") is not None and p.get("rut"):
            rut_map[p["id"]] = p["rut"]
            try:
                rut_map[int(p["id"])] = p["rut"]
            except (ValueError, TypeError):
                pass
            try:
                rut_map[str(p["id"])] = p["rut"]
            except (ValueError, TypeError):
                pass
    for data in pagos_ordenados:
        data["cuenta"] = cuenta_map.get(data["proveedor_nombre"], "")
        # Asignar rut_proveedor usando el ID del proveedor
        data["rut_proveedor"] = rut_map.get(data.get("proveedor"), "-")

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

    # NUEVA LÓGICA: Consultar tabla ingresos para determinar FAC. PAGO
    try:
        # Obtener todos los ingreso_ids únicos (excluyendo None)
        ingreso_ids = set(p.get("ingreso_id") for p in pagos_ordenados if p.get("ingreso_id") is not None)
        
        fac_pago_map = {}
        if ingreso_ids:
            # Consulta batch para obtener fac_pendiente de todos los ingresos
            res_ingresos = supabase.table("ingresos").select("id, fac_pendiente").in_("id", list(ingreso_ids)).execute()
            
            # Crear mapa: ingreso_id -> "SI" si fac_pendiente es válido (1, "1", true, etc.)
            for ing in (res_ingresos.data or []):
                ingreso_id = ing.get("id")
                fac_pendiente = ing.get("fac_pendiente")
                
                # Manejar diferentes tipos de datos para fac_pendiente
                es_pendiente = False
                if fac_pendiente is not None:
                    # Convertir a string y verificar si es "1" (valor esperado en la BD)
                    fac_str = str(fac_pendiente).strip()
                    es_pendiente = fac_str == "1"
                
                fac_pago_map[ingreso_id] = "SI" if es_pendiente else ""
                
    except Exception as e:
        print(f"[ERROR] Consulta ingresos para FAC. PAGO: {e}")
        fac_pago_map = {}

    # Calcular saldo pendiente para cada orden
    for data in pagos_ordenados:
        num = data["orden_numero"]
        total_abonado = abonos_map.get(num, 0)
        data["total_abonado"] = total_abonado
        
        # Si existe fecha_pago → saldo = 0, sino saldo = total - abonos
        data["saldo_pendiente"] = 0 if data.get("fecha_pago") else max(0, data["total_pago"] - total_abonado)
        
        # Asignar FAC. PAGO basado en ingreso_id
        ingreso_id = data.get("ingreso_id")
        data["fac_pago"] = fac_pago_map.get(ingreso_id, "")

    return pagos_ordenados

# --- FUNCION AUXILIAR PARA SUMAR SALDO PENDIENTE POR PROYECTO ---
def saldo_penproyecto(pagos):
    """
    Recibe una lista de pagos (diccionarios) y retorna un diccionario
    con el total de saldo pendiente agrupado por proyecto.
    """
    resultado = {}
    for pago in pagos:
        proyecto = pago.get("proyecto")
        saldo = pago.get("saldo_pendiente", 0)
        if proyecto:
            resultado[proyecto] = resultado.get(proyecto, 0) + saldo
    # Filtrar solo proyectos con saldo pendiente mayor a 1
    resultado_filtrado = {k: v for k, v in resultado.items() if v > 1}
    return resultado_filtrado

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

    # Calcular el saldo pendiente agrupado por proyecto
    saldo_por_proyecto = saldo_penproyecto(pagos)

    # Datos adicionales para el template
    proveedores_unicos = sorted(set(p["proveedor_nombre"] for p in pagos))
    proyectos_unicos = sorted(set(p["proyecto"] for p in pagos))

    # Calcular fecha máxima para el input de fecha (hoy + 7 días)
    fecha_maxima = (date.today() + timedelta(days=7)).isoformat()

    # Permisos: solo puede editar si tiene el módulo 'pagos'
    puede_editar = 'pagos' in modulos_usuario

    # Variables de paginación para compatibilidad con el template
    # Como el código restaurado obtiene todos los registros de una vez,
    # simulamos una sola página con todos los datos
    total_registros = len(pagos)
    page = 1
    per_page = total_registros if total_registros > 0 else 50
    total_pages = 1

    return render_template(
        "pagos.html",
        pagos=pagos,
        fecha_maxima=fecha_maxima,
        proveedores_unicos=proveedores_unicos,
        proyectos_unicos=proyectos_unicos,
        filtros_activos=filtros,
        total_pendiente=total_pendiente,
        saldo_por_proyecto=saldo_por_proyecto,
        puede_editar=puede_editar,
        date=date,
        # Variables de paginación requeridas por el template
        total_registros=total_registros,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )

@login_required
@bp_pagos.route("/pagos/update", methods=["POST"])
@require_modulo('pagos')
def update_pagos():
    supabase = current_app.config["SUPABASE"]
    
    # Detectar si es JSON o FormData
    if request.content_type and 'application/json' in request.content_type:
        # Recibir datos JSON (más eficiente)
        data = request.get_json()
        print(f"[DEBUG] Datos JSON recibidos: {data}")
        if data and 'cambios' in data:
            nums = [str(cambio['orden_numero']) for cambio in data['cambios']]
            fechas = [cambio['fecha_pago'] for cambio in data['cambios']]
            print(f"[DEBUG] Procesados - nums: {nums}, fechas: {fechas}")
        else:
            nums = []
            fechas = []
    else:
        # Recibir datos FormData (método tradicional)
        nums = request.form.getlist("orden_numero[]")
        fechas = request.form.getlist("fecha_pago[]")
        print(f"[DEBUG] FormData recibido - nums: {nums}, fechas: {fechas}")
    
    # Protección contra envío vacío o duplicado
    if not nums or len(nums) == 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": "No se enviaron datos para actualizar."}), 400
        else:
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
            # CRÍTICO: Solo eliminar fechas si el usuario REALMENTE las borró
            # No eliminar fechas de órdenes que simplemente están en el formulario sin cambios
            if fecha_actual is not None:  # Solo si había una fecha antes
                # NUEVA LÓGICA: Solo eliminar si el usuario envió explícitamente un campo vacío
                # que antes tenía una fecha (esto indicaría intención de borrar)
                # 
                # Para evitar borrados accidentales, solo eliminamos fechas si:
                # 1. Hay menos de 10 órdenes en el formulario (actualización pequeña)
                # 2. O si se puede verificar que fue intencional
                
                if len(nums) <= 10:  # Actualización pequeña, probablemente intencional
                    if suma_abonos > 0:
                        ordenes_con_abonos.append(num)
                        any_error = True
                        continue
                    else:
                        deletes.append(orden_numero)
                else:
                    # Actualización masiva - NO eliminar fechas para evitar bug
                    # Solo log para debug
                    print(f"[PROTECCIÓN] No eliminando fecha de OP {num} en actualización masiva")
            # Si no había fecha antes y sigue sin fecha, no hacer nada

    # Upsert masivo si hay datos válidos
    if upserts:
        try:
            print(f"[DEBUG] Intentando actualizar fechas en BD: {upserts}")
            result = supabase.table("fechas_de_pagos_op").upsert(upserts, on_conflict=["orden_numero"]).execute()
            print(f"[DEBUG] Resultado de upsert: {result}")
            print(f"[DEBUG] Datos actualizados: {result.data if hasattr(result, 'data') else 'Sin datos'}")
            
            # Log de actualización de fechas de pago
            registrar_log_actividad(
                accion="update",
                tabla_afectada="fechas_de_pagos_op",
                descripcion=f"Actualizó fechas de pago para OPs: {[u['orden_numero'] for u in upserts]}",
                datos_despues=upserts
            )
        except Exception as e:
            print(f"[ERROR] Error en upsert de fechas: {e}")
            any_error = True

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
        mensaje_error = ""
        if len(ordenes_con_abonos) == 1:
            mensaje_error = f"No puedes borrar la fecha de pago de la OP {ordenes_con_abonos[0]} porque tiene abonos registrados. Debes borrar los abonos primero."
        else:
            mensaje_error = f"No puedes borrar las fechas de pago de las OPs {', '.join(ordenes_con_abonos)} porque tienen abonos registrados. Debes borrar los abonos primero."
        
        # Responder con JSON si es llamada AJAX, sino usar flash tradicional
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": mensaje_error}), 400
        else:
            flash(mensaje_error, "danger")

    # Respuesta exitosa
    if not any_error:
        mensaje_exito = "Fechas de pago actualizadas con éxito"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": True, "message": mensaje_exito})
        else:
            flash(mensaje_exito, "success")
    
    return redirect(url_for("pagos.list_pagos"))


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
@bp_pagos.route('/pagos/test_fac_pago', methods=['GET'])
@require_modulo('pagos')
def test_fac_pago():
    """Endpoint simple para verificar datos FAC. PAGO"""
    pagos = get_pagos({"proveedor": "3121"})  # Filtrar orden 3121
    
    result = []
    for p in pagos:
        result.append({
            "orden_numero": p.get("orden_numero"),
            "ingreso_id": p.get("ingreso_id"),
            "fac_pago": p.get("fac_pago"),
            "proveedor_nombre": p.get("proveedor_nombre")
        })
    
    return jsonify({
        "success": True,
        "total": len(result),
        "data": result
    })

@login_required
@bp_pagos.route('/pagos/debug_fac_pago_masivo', methods=['GET'])
@require_modulo('pagos')
def debug_fac_pago_masivo():
    """Endpoint para debuggear la lógica masiva de FAC. PAGO como en get_pagos()"""
    supabase = current_app.config["SUPABASE"]
    
    debug_info = {
        "total_ordenes_consultadas": 0,
        "ordenes_con_ingreso_id": 0,
        "ordenes_sin_ingreso_id": 0,
        "ingreso_ids_unicos": [],
        "consulta_ingresos": [],
        "fac_pago_map": {},
        "muestra_ordenes": [],
        "errores": []
    }
    
    try:
        # Obtener primeras 10 órdenes para testing
        res_ordenes = supabase.table("orden_de_pago").select("orden_numero, ingreso_id").order("orden_numero", desc=True).limit(10).execute()
        ordenes = res_ordenes.data or []
        
        debug_info["total_ordenes_consultadas"] = len(ordenes)
        debug_info["muestra_ordenes"] = ordenes
        
        # Contar órdenes con y sin ingreso_id
        ordenes_con_ingreso = [o for o in ordenes if o.get("ingreso_id") is not None]
        ordenes_sin_ingreso = [o for o in ordenes if o.get("ingreso_id") is None]
        
        debug_info["ordenes_con_ingreso_id"] = len(ordenes_con_ingreso)
        debug_info["ordenes_sin_ingreso_id"] = len(ordenes_sin_ingreso)
        
        # Obtener ingreso_ids únicos
        ingreso_ids = set(o.get("ingreso_id") for o in ordenes_con_ingreso)
        debug_info["ingreso_ids_unicos"] = list(ingreso_ids)
        
        # Consultar tabla ingresos
        if ingreso_ids:
            res_ingresos = supabase.table("ingresos").select("id, fac_pendiente").in_("id", list(ingreso_ids)).execute()
            debug_info["consulta_ingresos"] = res_ingresos.data or []
            
            # Crear mapa como en get_pagos()
            fac_pago_map = {}
            for ing in (res_ingresos.data or []):
                ingreso_id = ing.get("id")
                fac_pendiente = ing.get("fac_pendiente")
                
                es_pendiente = False
                if fac_pendiente is not None:
                    if isinstance(fac_pendiente, int) and fac_pendiente == 1:
                        es_pendiente = True
                    else:
                        fac_str = str(fac_pendiente).strip().lower()
                        es_pendiente = fac_str in ["1", "true", "si", "yes"]
                
                fac_pago_map[ingreso_id] = "SI" if es_pendiente else ""
            
            debug_info["fac_pago_map"] = fac_pago_map
            
            # Aplicar el mapeo a las órdenes
            resultado_final = []
            for orden in ordenes:
                ingreso_id = orden.get("ingreso_id")
                fac_pago = fac_pago_map.get(ingreso_id, "")
                resultado_final.append({
                    "orden_numero": orden["orden_numero"],
                    "ingreso_id": ingreso_id,
                    "fac_pago": fac_pago
                })
            
            debug_info["resultado_final"] = resultado_final
        
        return jsonify(debug_info)
        
    except Exception as e:
        debug_info["errores"].append(f"Error en debug masivo: {str(e)}")
        return jsonify(debug_info), 500

@login_required
@bp_pagos.route('/pagos/debug_fac_pago/<int:orden_numero>', methods=['GET'])
@require_modulo('pagos')
def debug_fac_pago(orden_numero):
    """Endpoint para debuggear paso a paso la lógica de FAC. PAGO"""
    supabase = current_app.config["SUPABASE"]
    
    debug_info = {
        "orden_numero": orden_numero,
        "paso1_orden_de_pago": None,
        "paso2_ingreso_id": None,
        "paso3_consulta_ingresos": None,
        "paso4_fac_pendiente": None,
        "paso5_resultado_final": None,
        "errores": []
    }
    
    try:
        # PASO 1: Buscar en orden_de_pago
        res_orden = supabase.table("orden_de_pago").select("orden_numero, ingreso_id").eq("orden_numero", orden_numero).execute()
        debug_info["paso1_orden_de_pago"] = res_orden.data
        
        if not res_orden.data:
            debug_info["errores"].append("No se encontró la orden en tabla orden_de_pago")
            return jsonify(debug_info)
        
        # PASO 2: Extraer ingreso_id
        ingreso_id = res_orden.data[0].get("ingreso_id")
        debug_info["paso2_ingreso_id"] = {
            "valor": ingreso_id,
            "tipo": str(type(ingreso_id)),
            "es_none": ingreso_id is None
        }
        
        if ingreso_id is None:
            debug_info["errores"].append("ingreso_id es None - no hay relación con tabla ingresos")
            return jsonify(debug_info)
        
        # PASO 3: Consultar tabla ingresos
        res_ingresos = supabase.table("ingresos").select("id, fac_pendiente").eq("id", ingreso_id).execute()
        debug_info["paso3_consulta_ingresos"] = res_ingresos.data
        
        if not res_ingresos.data:
            debug_info["errores"].append(f"No se encontró el ingreso con id {ingreso_id} en tabla ingresos")
            return jsonify(debug_info)
        
        # PASO 4: Analizar fac_pendiente
        fac_pendiente = res_ingresos.data[0].get("fac_pendiente")
        debug_info["paso4_fac_pendiente"] = {
            "valor_crudo": fac_pendiente,
            "tipo": str(type(fac_pendiente)),
            "es_none": fac_pendiente is None,
            "como_string": str(fac_pendiente) if fac_pendiente is not None else "None",
            "como_string_lower": str(fac_pendiente).strip().lower() if fac_pendiente is not None else "None"
        }
        
        # PASO 5: Aplicar la lógica de evaluación
        es_pendiente = False
        if fac_pendiente is not None:
            if isinstance(fac_pendiente, int) and fac_pendiente == 1:
                es_pendiente = True
                debug_info["paso5_resultado_final"] = {"razon": "Es entero 1", "resultado": "SI"}
            else:
                fac_str = str(fac_pendiente).strip().lower()
                es_pendiente = fac_str in ["1", "true", "si", "yes"]
                debug_info["paso5_resultado_final"] = {
                    "razon": f"Como string: '{fac_str}' está en ['1', 'true', 'si', 'yes']",
                    "resultado": "SI" if es_pendiente else "VACIO",
                    "evaluacion": es_pendiente
                }
        else:
            debug_info["paso5_resultado_final"] = {"razon": "fac_pendiente es None", "resultado": "VACIO"}
        
        return jsonify(debug_info)
        
    except Exception as e:
        debug_info["errores"].append(f"Error en debug: {str(e)}")
        return jsonify(debug_info), 500

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