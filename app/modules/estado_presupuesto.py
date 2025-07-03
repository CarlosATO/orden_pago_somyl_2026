from flask import Blueprint, render_template, request, jsonify, current_app, flash, send_file
from datetime import datetime, date
import calendar
from collections import defaultdict
import io
import csv
import pandas as pd
from io import BytesIO
from app.modules.usuarios import require_modulo

bp_estado_presupuesto = Blueprint(
    'estado_presupuesto',
    __name__,
    url_prefix='/estado_presupuesto'
)

@bp_estado_presupuesto.route('', methods=['GET'])
@require_modulo('estado_presupuesto')
def show_estado():
    supabase = current_app.config['SUPABASE']

    # 1) Unir proyectos de presupuesto y orden_de_pago
    pres_proj = supabase.table('presupuesto').select('proyecto').execute().data or []
    pay_proj = supabase.table('orden_de_pago').select('proyecto').execute().data or []
    # Recojo todos los valores y los convierto a enteros, filtrando inválidos
    raw_projects = {r['proyecto'] for r in pres_proj} | {r['proyecto'] for r in pay_proj}
    proj_ids = set()
    for p in raw_projects:
        try:
            proj_ids.add(int(p))
        except (TypeError, ValueError):
            continue
    # Mapeo IDs a nombres legibles
    proj_res_names = supabase.table('proyectos') \
        .select('id,proyecto') \
        .in_('id', list(proj_ids)) \
        .execute().data or []
    id_to_nombre_proj = {r['id']: r['proyecto'] for r in proj_res_names}
    # Invertir mapping para nombres a IDs
    name_to_id = {name: pid for pid, name in id_to_nombre_proj.items()}
    # Construyo lista de tuplas (id_str, nombre) para la plantilla
    proyectos = [(str(pid), id_to_nombre_proj.get(pid, f'Proyecto {pid}'))
                 for pid in sorted(proj_ids)]

    # 2) Parámetros de filtro: proyectos, desde y hasta
    raw_selected = request.args.getlist('proyecto')
    selected = []
    for val in raw_selected:
        try:
            selected.append(int(val))
        except ValueError:
            flash(f"Valor de proyecto inválido: {val}", "warning")

    desde = request.args.get('desde')  # formato 'Mon-yy'
    hasta = request.args.get('hasta')
    fmt = '%b-%y'
    fecha_desde = None
    fecha_hasta = None
    try:
        if desde:
            dt = datetime.strptime(desde, fmt)
            fecha_desde = dt.replace(day=1).date().isoformat()
        if hasta:
            dt2 = datetime.strptime(hasta, fmt)
            year, month = dt2.year, dt2.month
            last_day = calendar.monthrange(year, month)[1]
            fecha_hasta = date(year, month, last_day).isoformat()
    except ValueError:
        flash("Rango de fechas inválido", "warning")

    # Inicializar estructuras
    table = {}
    months = []
    row_totals = {}
    col_totals = {}
    grand_totals = {'presupuesto': 0, 'real': 0}

    if selected:
        # 3) Consulta presupuestos con rangos
        # Convertir selected IDs a nombres para filtrar presupuesto (tabla usa nombres)
        selected_names = [id_to_nombre_proj.get(pid) for pid in selected if pid in id_to_nombre_proj]
        query_pre = supabase.table('presupuesto') \
            .select('proyecto,item,fecha,monto') \
            .in_('proyecto', selected_names)
        if fecha_desde:
            query_pre = query_pre.gte('fecha', fecha_desde)
        if fecha_hasta:
            query_pre = query_pre.lte('fecha', fecha_hasta)
        presupuestos = query_pre.execute().data or []

        # 4) Consulta pagos with rangos
        query_pay = supabase.table('orden_de_pago').select('proyecto,item,fecha_factura,costo_final_con_iva').in_('proyecto', selected)
        if fecha_desde:
            query_pay = query_pay.gte('fecha_factura', fecha_desde)
        if fecha_hasta:
            query_pay = query_pay.lte('fecha_factura', fecha_hasta)
        pagos = query_pay.execute().data or []

        # 4b) Consulta gastos directos con rangos
        query_gd = supabase.table('gastos_directos').select('proyecto_id,item_id,fecha,mes,monto')
        if selected:
            query_gd = query_gd.in_('proyecto_id', selected)
        if fecha_desde:
            query_gd = query_gd.gte('fecha', fecha_desde)
        if fecha_hasta:
            query_gd = query_gd.lte('fecha', fecha_hasta)
        gastos_directos = query_gd.execute().data or []

        # Normalizar gastos directos: mes en formato %b-%y
        def gd_month_key(gd):
            meses = {
                'Enero': 'Jan', 'Febrero': 'Feb', 'Marzo': 'Mar', 'Abril': 'Apr',
                'Mayo': 'May', 'Junio': 'Jun', 'Julio': 'Jul', 'Agosto': 'Aug',
                'Septiembre': 'Sep', 'Octubre': 'Oct', 'Noviembre': 'Nov', 'Diciembre': 'Dec'
            }
            mes_esp = gd['mes']
            mes_abbr = meses.get(mes_esp, mes_esp[:3].capitalize())
            anio = str(datetime.fromisoformat(gd['fecha']).year)[-2:]
            return f"{mes_abbr}-{anio}"

        # Unificar estructura con pagos
        pagos += [
            {
                'proyecto': gd['proyecto_id'],
                'item': gd['item_id'],
                'fecha_factura': gd['fecha'],
                'costo_final_con_iva': gd['monto'],
                '_is_gasto_directo': True,
                'mes': gd_month_key(gd)  # <-- agrega el mes correcto
            }
            for gd in gastos_directos
        ]

        # 5) Generar lista de meses únicos
        def month_key(fecha_str):
            return datetime.fromisoformat(fecha_str).strftime('%b-%y')

        mes_set = {month_key(r['fecha']) for r in presupuestos} | {
            r['mes'] if 'mes' in r and r['mes'] else month_key(r['fecha_factura']) for r in pagos
        }
        months = sorted(mes_set, key=lambda m: datetime.strptime(m, '%b-%y'))

        # 6) Mapear IDs de item a nombre (tipo)
        # Recolectar raw item IDs (pueden ser strings)
        raw_item_ids = {r['item'] for r in presupuestos} | {r['item'] for r in pagos}
        # Separar IDs numéricos
        numeric_item_ids = set()
        for iid in raw_item_ids:
            try:
                numeric_item_ids.add(int(iid))
            except (TypeError, ValueError):
                continue
        # Consultar solo los IDs numéricos
        items_res = supabase.table('item').select('id,tipo').in_('id', list(numeric_item_ids)).execute().data or []
        id_to_tipo = {i['id']: i['tipo'] for i in items_res}
        # Para items no numéricos, usaremos la cadena directamente como tipo
        # Generar función auxiliar para obtener tipo legible:
        def get_tipo(item_val):
            try:
                iv = int(item_val)
                return id_to_tipo.get(iv, f'Item {iv}')
            except (TypeError, ValueError):
                return str(item_val)

        # 7) Preparar acumulación de datos
        data = defaultdict(lambda: defaultdict(lambda: {m: {'presupuesto': 0, 'real': 0} for m in months}))
        totals_by_month = {m: {'presupuesto': 0, 'real': 0} for m in months}

        # 8) Acumular presupuestos
        for r in presupuestos:
            # Convertir nombre de proyecto a ID
            raw_prj_name = r['proyecto']
            prj = name_to_id.get(raw_prj_name)
            if prj is None:
                continue
            raw_itm = r['item']
            m = month_key(r['fecha'])
            tipo_key = get_tipo(raw_itm)
            data[prj][tipo_key][m]['presupuesto'] += r['monto']
            totals_by_month[m]['presupuesto'] += r['monto']
            grand_totals['presupuesto'] += r['monto']

        # 9) Acumular pagos
        for r in pagos:
            # Asegurar prj ID como entero
            try:
                prj = int(r['proyecto'])
            except (TypeError, ValueError):
                continue
            raw_itm = r['item']
            m = r['mes'] if 'mes' in r and r['mes'] else month_key(r['fecha_factura'])
            tipo_key = get_tipo(raw_itm)
            data[prj][tipo_key][m]['real'] += r['costo_final_con_iva']
            totals_by_month[m]['real'] += r['costo_final_con_iva']
            grand_totals['real'] += r['costo_final_con_iva']

        # 10) Calcular totales por fila
        for prj, items in data.items():
            row_totals[prj] = {}
            table[prj] = {}
            for tipo_key, meses in items.items():
                table[prj][tipo_key] = meses
                sum_pre = sum(v['presupuesto'] for v in meses.values())
                sum_real = sum(v['real'] for v in meses.values())
                row_totals[prj][tipo_key] = {'presupuesto': sum_pre, 'real': sum_real}

        col_totals = totals_by_month

    # Convertir selected a strings para la plantilla
    selected_str = [str(x) for x in selected]

    # Calcular resumen de presupuesto cuando solo hay un proyecto seleccionado
    resumen_presupuesto = None
    resumen_real = None
    if len(selected) == 1:
        # 1. Buscar venta presupuestada del proyecto
        prj_id = selected[0]
        venta = 0
        venta_q = supabase.table('proyectos').select('venta').eq('id', prj_id).execute().data or []
        if venta_q and 'venta' in venta_q[0]:
            try:
                venta = int(venta_q[0]['venta'] or 0)
            except Exception:
                venta = 0

        # 2. Gasto presupuestado (suma de todos los presupuestos del proyecto seleccionado)
        gasto_presup = 0
        for items in row_totals.get(prj_id, {}).values():
            try:
                gasto_presup += int(items['presupuesto'] or 0)
            except Exception:
                continue
        # 3. Saldo
        try:
            saldo_presup = int(venta or 0) - int(gasto_presup or 0)
        except Exception:
            saldo_presup = 0

        resumen_presupuesto = {
            'venta': int(venta or 0),
            'gasto': int(gasto_presup or 0),
            'saldo': int(saldo_presup or 0),
        }

        # Calcular resumen real
        # 1. Producción actual: traer desde la tabla proyectos
        prod_val = 0
        prod_q = supabase.table('proyectos').select('produccion').eq('id', prj_id).execute().data or []
        if prod_q and 'produccion' in prod_q[0]:
            try:
                prod_val = int(prod_q[0]['produccion'] or 0)
            except Exception:
                prod_val = 0

        # 2. Gasto real (suma de todos los reales del proyecto en este informe)
        gasto_real = 0
        for items in row_totals.get(prj_id, {}).values():
            try:
                gasto_real += int(items['real'] or 0)
            except Exception:
                continue
        # 3. Saldo actual
        try:
            saldo_real = int(prod_val or 0) - int(gasto_real or 0)
        except Exception:
            saldo_real = 0

        resumen_real = {
            'produccion': int(prod_val or 0),
            'gasto_real': int(gasto_real or 0),
            'saldo_real': int(saldo_real or 0),
            'editable': True,  # Puedes cambiar lógica si luego agregas roles
            'proyecto': prj_id
        }

    # Casting seguro de resumen_presupuesto antes de pasar a la plantilla
    # Nos aseguramos que venta, gasto y saldo sean int (o 0 si vienen mal tipeados)
    safe_resumen_presupuesto = (
        {
            'venta': int(resumen_presupuesto.get('venta', 0)),
            'gasto': int(resumen_presupuesto.get('gasto', 0)),
            'saldo': int(resumen_presupuesto.get('saldo', 0))
        } if resumen_presupuesto else None
    )
    # Casting seguro de resumen_real antes de pasar a la plantilla
    # Nos aseguramos que produccion, gasto_real y saldo_real sean int (o 0 si vienen mal tipeados)
    safe_resumen_real = (
        {
            'produccion': int(resumen_real.get('produccion', 0)),
            'gasto_real': int(resumen_real.get('gasto_real', 0)),
            'saldo_real': int(resumen_real.get('saldo_real', 0)),
            'editable': resumen_real.get('editable', True),
            'proyecto': resumen_real.get('proyecto', None)
        } if resumen_real else None
    )
    return render_template(
        'estado_presupuesto.html',
        proyectos=proyectos,
        selected=selected_str,
        months=months,
        desde=desde,
        hasta=hasta,
        table=table,
        row_totals=row_totals,
        col_totals=col_totals,
        grand_totals=grand_totals,
        project_names=id_to_nombre_proj,
        resumen_presupuesto=safe_resumen_presupuesto,  # Cast a int por seguridad
        resumen_real=safe_resumen_real  # Cast a int por seguridad
    )

@bp_estado_presupuesto.route('/update_presupuesto', methods=['POST'])
@require_modulo('estado_presupuesto')
def update_presupuesto():
    data = request.get_json()
    proyecto = data.get('proyecto')
    item = data.get('item')
    month = data.get('month')
    value = data.get('value')

    try:
        dt = datetime.strptime(month, '%b-%y')
        fecha_iso = dt.replace(day=1).date().isoformat()
    except ValueError:
        return jsonify(success=False)

    res = current_app.config['SUPABASE'] \
        .table('presupuesto') \
        .update({'monto': value}) \
        .eq('proyecto', proyecto) \
        .eq('item', item) \
        .eq('fecha', fecha_iso) \
        .execute()

    return jsonify(success=not getattr(res, 'error', None))


@bp_estado_presupuesto.route('/update_produccion', methods=['POST'])
@require_modulo('estado_presupuesto')
def update_produccion():
    data = request.get_json()
    proyecto = data.get('proyecto')
    produccion = data.get('produccion')
    try:
        prj_id = int(proyecto)
        prod_val = int(produccion)
    except (TypeError, ValueError):
        return jsonify(success=False)
    res = current_app.config['SUPABASE'] \
        .table('proyectos') \
        .update({'produccion': prod_val}) \
        .eq('id', prj_id) \
        .execute()
    return jsonify(success=not getattr(res, 'error', None))


@bp_estado_presupuesto.route('/export', methods=['GET'], endpoint='export_presupuesto')
@require_modulo('estado_presupuesto')
def export_presupuesto():
    # Leer parámetros de filtro y mapear a nombres de proyecto
    selected_ids = request.args.get('proyecto', '').split(',')
    proj_ids = []
    for s in selected_ids:
        try:
            proj_ids.append(int(s))
        except ValueError:
            continue

    proj_name_res = current_app.config['SUPABASE'].table('proyectos') \
        .select('id,proyecto') \
        .in_('id', proj_ids) \
        .execute().data or []
    id_to_nombre_proj = {r['id']: r['proyecto'] for r in proj_name_res}
    name_to_id = {name: pid for pid, name in id_to_nombre_proj.items()}

    desde = request.args.get('desde')
    hasta = request.args.get('hasta')
    fmt = '%b-%y'
    desde_iso = hasta_iso = None
    if desde:
        dt = datetime.strptime(desde, fmt)
        desde_iso = dt.replace(day=1).date().isoformat()
    if hasta:
        dt2 = datetime.strptime(hasta, fmt)
        year, month = dt2.year, dt2.month
        last_day = calendar.monthrange(year, month)[1]
        hasta_iso = date(year, month, last_day).isoformat()

    # Usa la función auxiliar para obtener la estructura correcta
    table, months, project_names = build_estado_presupuesto(
        current_app.config['SUPABASE'],
        proj_ids,
        desde_iso,
        hasta_iso,
        id_to_nombre_proj,
        name_to_id
    )

    # Construir filas para Excel
    rows = []
    for prj, items in table.items():
        for item, meses in items.items():
            row = {'proyecto': project_names.get(prj, prj), 'item': item}
            for m in months:
                row[m+' Presupuesto'] = meses[m]['presupuesto']
                row[m+' Real'] = meses[m]['real']
            rows.append(row)

    # Crear DataFrame y totales
    df = pd.DataFrame(rows)
    for suffix in [' Presupuesto', ' Real']:
        tot_cols = [col for col in df.columns if col.endswith(suffix)]
        df['Total'+suffix] = df[tot_cols].sum(axis=1)
    total_row = {'proyecto': '', 'item': 'Totales →'}
    for col in df.columns[2:]:
        total_row[col] = df[col].sum()
    df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

    # Exportar a Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Estado de Presupuesto', index=False)
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='presupuesto.xlsx'
    )

def build_estado_presupuesto(supabase, selected, fecha_desde, fecha_hasta, id_to_nombre_proj, name_to_id):
    # 3) Consulta presupuestos con rangos
    selected_names = [id_to_nombre_proj.get(pid) for pid in selected if pid in id_to_nombre_proj]
    query_pre = supabase.table('presupuesto') \
        .select('proyecto,item,fecha,monto') \
        .in_('proyecto', selected_names)
    if fecha_desde:
        query_pre = query_pre.gte('fecha', fecha_desde)
    if fecha_hasta:
        query_pre = query_pre.lte('fecha', fecha_hasta)
    presupuestos = query_pre.execute().data or []

    # 4) Consulta pagos with rangos
    query_pay = supabase.table('orden_de_pago').select('proyecto,item,fecha_factura,costo_final_con_iva').in_('proyecto', selected)
    if fecha_desde:
        query_pay = query_pay.gte('fecha_factura', fecha_desde)
    if fecha_hasta:
        query_pay = query_pay.lte('fecha_factura', fecha_hasta)
    pagos = query_pay.execute().data or []

    # 4b) Consulta gastos directos con rangos
    query_gd = supabase.table('gastos_directos').select('proyecto_id,item_id,fecha,mes,monto')
    if selected:
        query_gd = query_gd.in_('proyecto_id', selected)
    if fecha_desde:
        query_gd = query_gd.gte('fecha', fecha_desde)
    if fecha_hasta:
        query_gd = query_gd.lte('fecha', fecha_hasta)
    gastos_directos = query_gd.execute().data or []

    def gd_month_key(gd):
        meses = {
            'Enero': 'Jan', 'Febrero': 'Feb', 'Marzo': 'Mar', 'Abril': 'Apr',
            'Mayo': 'May', 'Junio': 'Jun', 'Julio': 'Jul', 'Agosto': 'Aug',
            'Septiembre': 'Sep', 'Octubre': 'Oct', 'Noviembre': 'Nov', 'Diciembre': 'Dec'
        }
        mes_esp = gd['mes']
        mes_abbr = meses.get(mes_esp, mes_esp[:3].capitalize())
        anio = str(datetime.fromisoformat(gd['fecha']).year)[-2:]
        return f"{mes_abbr}-{anio}"

    pagos += [
        {
            'proyecto': gd['proyecto_id'],
            'item': gd['item_id'],
            'fecha_factura': gd['fecha'],
            'costo_final_con_iva': gd['monto'],
            '_is_gasto_directo': True,
            'mes': gd_month_key(gd)
        }
        for gd in gastos_directos
    ]

    def month_key(fecha_str):
        return datetime.fromisoformat(fecha_str).strftime('%b-%y')

    mes_set = {month_key(r['fecha']) for r in presupuestos} | {
        r['mes'] if 'mes' in r and r['mes'] else month_key(r['fecha_factura']) for r in pagos
    }
    months = sorted(mes_set, key=lambda m: datetime.strptime(m, '%b-%y'))

    # Mapear IDs de item a nombre (tipo)
    raw_item_ids = {r['item'] for r in presupuestos} | {r['item'] for r in pagos}
    numeric_item_ids = set()
    for iid in raw_item_ids:
        try:
            numeric_item_ids.add(int(iid))
        except (TypeError, ValueError):
            continue
    items_res = supabase.table('item').select('id,tipo').in_('id', list(numeric_item_ids)).execute().data or []
    id_to_tipo = {i['id']: i['tipo'] for i in items_res}
    def get_tipo(item_val):
        try:
            iv = int(item_val)
            return id_to_tipo.get(iv, f'Item {iv}')
        except (TypeError, ValueError):
            return str(item_val)

    # Acumulación
    from collections import defaultdict
    data = defaultdict(lambda: defaultdict(lambda: {m: {'presupuesto': 0, 'real': 0} for m in months}))
    for r in presupuestos:
        raw_prj_name = r['proyecto']
        prj = name_to_id.get(raw_prj_name)
        if prj is None:
            continue
        raw_itm = r['item']
        m = month_key(r['fecha'])
        tipo_key = get_tipo(raw_itm)
        data[prj][tipo_key][m]['presupuesto'] += r['monto']
    for r in pagos:
        try:
            prj = int(r['proyecto'])
        except (TypeError, ValueError):
            continue
        raw_itm = r['item']
        m = r['mes'] if 'mes' in r and r['mes'] else month_key(r['fecha_factura'])
        tipo_key = get_tipo(raw_itm)
        data[prj][tipo_key][m]['real'] += r['costo_final_con_iva']

    # Construir tabla igual que en show_estado
    table = {}
    for prj, items in data.items():
        table[prj] = {}
        for tipo_key, meses in items.items():
            table[prj][tipo_key] = meses

    return table, months, id_to_nombre_proj

@bp_estado_presupuesto.route('/prueba')
def prueba():
    supabase = current_app.config['SUPABASE']
    desde = '2023-01-01'
    hasta = '2023-12-31'
    proj_ids = [1, 2, 3]  # Proyectos de ejemplo

    # 1) Obtener nombres de proyectos
    proj_res_names = supabase.table('proyectos') \
        .select('id,proyecto') \
        .in_('id', proj_ids) \
        .execute().data or []
    id_to_nombre_proj = {r['id']: r['proyecto'] for r in proj_res_names}
    name_to_id = {name: pid for pid, name in id_to_nombre_proj.items()}

    # Usa la función auxiliar para obtener la estructura correcta
    table, months, project_names = build_estado_presupuesto(
        current_app.config['SUPABASE'],
        proj_ids,
        desde_iso if desde else None,
        hasta_iso if hasta else None,
        id_to_nombre_proj,
        name_to_id
    )

    rows = []
    for prj, items in table.items():
        for item, meses in items.items():
            row = {'proyecto': project_names.get(prj, prj), 'item': item}
            for m in months:
                row[m+' Presupuesto'] = meses[m]['presupuesto']
                row[m+' Real'] = meses[m]['real']
            rows.append(row)

    # Crear DataFrame y totales
    df = pd.DataFrame(rows)
    for suffix in [' Presupuesto', ' Real']:
        tot_cols = [col for col in df.columns if col.endswith(suffix)]
        df['Total'+suffix] = df[tot_cols].sum(axis=1)
    total_row = {'proyecto': '', 'item': 'Totales →'}
    for col in df.columns[2:]:
        total_row[col] = df[col].sum()
    df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

    # Exportar a Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Estado de Presupuesto', index=False)
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='presupuesto.xlsx'
    )