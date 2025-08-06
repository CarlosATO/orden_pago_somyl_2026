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
from openpyxl import Workbook
from app.modules.usuarios import require_modulo, get_modulos_usuario
from app.utils.static_data import get_cached_proveedores, get_cached_proyectos_with_id
from utils.logger import registrar_log_actividad

bp_pagos = Blueprint(
    "pagos", __name__,
    template_folder="../templates"
)

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

# Funciones de abonos simplificadas
@login_required
@bp_pagos.route('/abonos/<int:orden_numero>', methods=['GET'])
@require_modulo('pagos')
def get_abonos_op(orden_numero):
    supabase = current_app.config["SUPABASE"]
    try:
        res = supabase.table("abonos_op").select("id, orden_numero, monto_abono, fecha_abono, observacion, created_at").eq("orden_numero", orden_numero).order("fecha_abono", desc=False).execute()
        abonos = res.data if hasattr(res, "data") and res.data else []
        
        response = jsonify(success=True, abonos=abonos)
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

        # Validaciones de suma y total
        res_abonos = supabase.table("abonos_op").select("monto_abono").eq("orden_numero", orden_numero).execute()
        suma_abonos = sum(int(round(float(a.get("monto_abono") or 0))) for a in (res_abonos.data or []))

        res_pago = supabase.table("orden_de_pago").select("costo_final_con_iva").eq("orden_numero", orden_numero).limit(1).execute()
        if not res_pago.data:
            return jsonify(success=False, error="No se encontró el total de la orden."), 400
        total_pago = int(round(float(res_pago.data[0].get("costo_final_con_iva") or 0)))

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

        # Si completa el total, registrar fecha_pago automáticamente
        if nueva_suma == total_pago:
            supabase.table("fechas_de_pagos_op").upsert({"orden_numero": orden_numero, "fecha_pago": fecha}, on_conflict=["orden_numero"]).execute()

        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@login_required
@bp_pagos.route('/abonos/<int:abono_id>', methods=['DELETE'])
@require_modulo('pagos')
def eliminar_abono_op(abono_id):
    supabase = current_app.config["SUPABASE"]
    try:
        res_abono = supabase.table("abonos_op").select("orden_numero").eq("id", abono_id).limit(1).execute()
        if not res_abono.data:
            return jsonify(success=False, error="No se encontró el abono."), 400
        orden_numero = res_abono.data[0]["orden_numero"]

        res = supabase.table("abonos_op").delete().eq("id", abono_id).execute()
        if hasattr(res, "error") and res.error:
            return jsonify(success=False, error=str(res.error)), 500

        # Verificar suma restante
        res_abonos_restantes = supabase.table("abonos_op").select("monto_abono").eq("orden_numero", orden_numero).execute()
        suma_restante = sum(int(round(float(a.get("monto_abono") or 0))) for a in (res_abonos_restantes.data or []))
        
        if suma_restante > 0:
            res_pago = supabase.table("orden_de_pago").select("costo_final_con_iva").eq("orden_numero", orden_numero).limit(1).execute()
            total_pago = int(round(float(res_pago.data[0].get("costo_final_con_iva") or 0))) if res_pago.data else 0
            
            if suma_restante < total_pago:
                supabase.table("fechas_de_pagos_op").delete().eq("orden_numero", orden_numero).execute()
        else:
            supabase.table("fechas_de_pagos_op").delete().eq("orden_numero", orden_numero).execute()

        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

# Endpoint simple para testing
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
