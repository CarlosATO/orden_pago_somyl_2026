from flask import Blueprint, request, jsonify, current_app, render_template
from collections import defaultdict
from backend.utils.decorators import token_required
from backend.utils.cache import clear_cache
import re

"""
Módulo de proveedores con rutas para CRUD, búsqueda y validación de RUT.

Rutas principales (resumen):
  / (GET) - formulario/lista
  /new (POST) - crear
  /edit/<id> (GET, POST) - editar
  /api/search (GET) - select2
  /api/validate_rut (POST) - validar RUT
  /api/todos (GET, protegido) - devuelve todos los proveedores (id, nombre)
  /api/buscar (GET, protegido) - búsqueda dinámica para react-select
"""

bp = Blueprint("proveedores", __name__, template_folder="../templates/proveedores")


def validate_rut(rut_raw: str):
    """Valida y formatea un RUT chileno.

    Devuelve (True, formatted_rut) o (False, error_message)
    """
    if not rut_raw:
        return False, "RUT vacío"

    # Normalizar: quitar espacios y puntos, mayúsculas
    rut = re.sub(r"[\.\s]", "", rut_raw).upper()

    # Debe tener un guión separando cuerpo y dígito verificador o ser al menos 2 chars
    if '-' in rut:
        parts = rut.split('-')
        if len(parts) != 2:
            return False, "Formato RUT inválido"
        cuerpo, dv = parts[0], parts[1]
    else:
        cuerpo, dv = rut[:-1], rut[-1]

    if not cuerpo.isdigit():
        return False, "Cuerpo del RUT debe ser numérico"

    # Calcular dígito verificador
    reversed_digits = map(int, reversed(cuerpo))
    factors = [2,3,4,5,6,7]
    s = 0
    factor_index = 0
    for d in reversed_digits:
        s += d * factors[factor_index]
        factor_index = (factor_index + 1) % len(factors)

    r = 11 - (s % 11)
    if r == 11:
        dv_calc = '0'
    elif r == 10:
        dv_calc = 'K'
    else:
        dv_calc = str(r)

    if dv_calc != dv:
        return False, f"DV inválido (esperado {dv_calc})"

    # Formatear con puntos y guión: 12.345.678-9
    cuerpo_int = int(cuerpo)
    formatted_cuerpo = f"{cuerpo_int:,}".replace(',', '.')
    formatted = f"{formatted_cuerpo}-{dv_calc}"
    return True, formatted


def normalize_data(data: dict):
    """Normaliza campos: mayúsculas para nombre/dirección/comuna/contacto,
    minúsculas para correo, convierte subcontrato a 1/0.
    Devuelve dict nuevo.
    """
    out = data.copy()
    for k in ['nombre', 'direccion', 'comuna', 'contacto']:
        if k in out and out[k] is not None:
            out[k] = str(out[k]).upper()

    if 'correo' in out and out['correo']:
        out['correo'] = str(out['correo']).lower()

    if 'subcontrato' in out:
        val = out.get('subcontrato')
        if isinstance(val, str):
            val_low = val.strip().lower()
            out['subcontrato'] = 1 if val_low in ('1', 'si', 'sí', 'true', 'yes') else 0
        else:
            out['subcontrato'] = 1 if bool(val) else 0

    return out


def registrar_log_actividad(user_id: int, accion: str, detalle: dict):
    """Registra un log de actividad en la tabla 'actividad_logs' si existe,
    o lo escribe en el logger como fallback.
    """
    supabase = current_app.config.get('SUPABASE')
    payload = {
        'user_id': user_id,
        'accion': accion,
        'detalle': detalle
    }
    try:
        if supabase:
            # Intentar insertar en una tabla 'actividad_logs' (si está disponible)
            try:
                supabase.table('actividad_logs').insert(payload).execute()
            except Exception:
                # Si falla (tabla no existe), caemos al logger
                current_app.logger.info(f"Actividad: {accion} - {detalle}")
        else:
            current_app.logger.info(f"Actividad: {accion} - {detalle}")
    except Exception:
        current_app.logger.info(f"Actividad(FALLBACK): {accion} - {detalle}")


def invalidate_select2_cache(name: str):
    """Invalidar cache relacionado a select2/autocomplete.
    Llama a clear_cache con prefijos conocidos.
    """
    try:
        # Intentamos limpiar claves con prefijo 'select2:<name>' y '<name>' también
        clear_cache(f"select2:{name}")
        clear_cache(name)
    except Exception:
        current_app.logger.info(f"No se pudo invalidar cache para {name}")


# ------------------ RUTAS PRINCIPALES (form-like) ------------------
@bp.route('/', methods=['GET'])
def proveedores_index():
    """Devuelve la lista y placeholder para formulario (frontend React usa APIs)."""
    # Para compatibilidad con plantillas, podríamos renderizar, pero devolvemos JSON
    supabase = current_app.config['SUPABASE']
    try:
        res = supabase.table('proveedores').select('id, nombre, rut').order('nombre').execute()
        items = res.data or []
        proveedores = [{'id': p.get('id'), 'nombre': p.get('nombre'), 'rut': p.get('rut')} for p in items]
        return jsonify({'success': True, 'data': proveedores})
    except Exception as e:
        current_app.logger.error(f"Error al listar proveedores desde index: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno'}), 500


@bp.route('/new', methods=['POST'])
def proveedores_new():
    data = request.get_json() or {}
    
    # Mapear campos del frontend a los de la BD
    if 'telefono' in data:
        data['fono'] = data.pop('telefono')
    if 'email' in data:
        data['correo'] = data.pop('email')
    
    # Normalizar y validar RUT
    rut_raw = data.get('rut')
    ok, resp = validate_rut(rut_raw)
    if not ok:
        return jsonify({'success': False, 'message': resp}), 400

    data['rut'] = resp
    data = normalize_data(data)

    supabase = current_app.config['SUPABASE']
    try:
        # Duplicado por RUT?
        dup = supabase.table('proveedores').select('id,nombre').eq('rut', data['rut']).execute()
        if dup.data:
            return jsonify({'success': False, 'message': 'Ya existe un proveedor con este RUT'}), 400

        # Nombre duplicado -> warning (no bloqueante)
        name_dup = supabase.table('proveedores').select('id').ilike('nombre', data['nombre']).execute()
        warning = None
        if name_dup.data:
            warning = 'Existe al menos un proveedor con nombre similar'

        res = supabase.table('proveedores').insert(data).execute()
        if res.data:
            created = res.data[0] if isinstance(res.data, list) and len(res.data) > 0 else res.data
            # Log y cache
            registrar_log_actividad(user_id=0, accion='crear_proveedor', detalle=created)
            invalidate_select2_cache('proveedores')
            out = {'success': True, 'data': created}
            if warning:
                out['warning'] = warning
            return jsonify(out)
        else:
            return jsonify({'success': False, 'message': 'Error al crear proveedor'}), 500

    except Exception as e:
        current_app.logger.error(f"Error crear proveedor: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno'}), 500


@bp.route('/edit/<int:proveedor_id>', methods=['GET', 'POST'])
def proveedores_edit(proveedor_id):
    supabase = current_app.config['SUPABASE']
    if request.method == 'GET':
        try:
            res = supabase.table('proveedores').select('*').eq('id', proveedor_id).single().execute()
            if res.data:
                # Mapear campos de BD a frontend
                data = res.data.copy()
                if 'fono' in data:
                    data['telefono'] = data['fono']
                    del data['fono']
                if 'correo' in data:
                    data['email'] = data['correo']
                    del data['correo']
                return jsonify({'success': True, 'data': data})
            return jsonify({'success': False, 'message': 'No encontrado'}), 404
        except Exception as e:
            current_app.logger.error(f"Error get proveedor {proveedor_id}: {str(e)}")
            return jsonify({'success': False, 'message': 'Error interno'}), 500

    # POST -> actualizar
    data = request.get_json() or {}
    
    # Mapear campos del frontend a los de la BD
    if 'telefono' in data:
        data['fono'] = data.pop('telefono')
    if 'email' in data:
        data['correo'] = data.pop('email')
    
    if 'rut' in data:
        ok, resp = validate_rut(data.get('rut'))
        if not ok:
            return jsonify({'success': False, 'message': resp}), 400
        data['rut'] = resp

    data = normalize_data(data)
    try:
        # Duplicado de RUT en otro id?
        if 'rut' in data:
            dup = supabase.table('proveedores').select('id').eq('rut', data['rut']).execute()
            if dup.data and any(d.get('id') != proveedor_id for d in dup.data):
                return jsonify({'success': False, 'message': 'Otro proveedor ya usa ese RUT'}), 400

        res = supabase.table('proveedores').update(data).eq('id', proveedor_id).execute()
        if res.data:
            registrar_log_actividad(user_id=0, accion='editar_proveedor', detalle={'id': proveedor_id, 'data': data})
            invalidate_select2_cache('proveedores')
            return jsonify({'success': True, 'data': res.data})
        else:
            return jsonify({'success': False, 'message': 'No se pudo actualizar'}), 404

    except Exception as e:
        current_app.logger.error(f"Error update proveedor {proveedor_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno'}), 500


# ------------------ API endpoints (search/validate/protected) ------------------
@bp.route('/api/search', methods=['GET'])
def api_search():
    term = (request.args.get('term') or '').strip()
    limit = int(request.args.get('limit', 20)) if request.args.get('limit') else 20
    if limit > 50:
        limit = 50

    supabase = current_app.config['SUPABASE']
    try:
        query = supabase.table('proveedores').select('id, nombre, rut')
        if term and len(term) >= 2:
            query = query.ilike('nombre', f"%{term}%")
        res = query.order('nombre').limit(limit).execute()
        items = res.data or []
        # Select2 expects { id, text }
        results = [{'id': p.get('id'), 'text': f"{p.get('nombre')} ({p.get('rut')})"} for p in items]
        return jsonify({'results': results})
    except Exception as e:
        current_app.logger.error(f"Error api_search proveedores: {str(e)}")
        return jsonify({'success': False, 'message': 'Error búsqueda'}), 500


@bp.route('/api/validate_rut', methods=['POST'])
def api_validate_rut():
    data = request.get_json() or {}
    rut = data.get('rut')
    ok, resp = validate_rut(rut)
    if ok:
        return jsonify({'success': True, 'rut': resp})
    return jsonify({'success': False, 'message': resp}), 400


@bp.route('/api/todos', methods=['GET'])
@token_required
def api_todos(current_user):
    supabase = current_app.config['SUPABASE']
    try:
        res = supabase.table('proveedores').select('id, nombre, rut, fono, correo, contacto, direccion, comuna, subcontrato, banco, cuenta, paguese_a').order('nombre').execute()
        items = res.data or []
        # Mapear campos de BD a frontend
        for item in items:
            if 'fono' in item:
                item['telefono'] = item['fono']
                del item['fono']
            if 'correo' in item:
                item['email'] = item['correo']
                del item['correo']
        return jsonify({'success': True, 'data': items})
    except Exception as e:
        current_app.logger.error(f"Error api_todos proveedores: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno'}), 500


@bp.route('/api/buscar', methods=['GET'])
@token_required
def api_buscar(current_user):
    term = (request.args.get('term') or '').strip()
    limit = int(request.args.get('limit', 20)) if request.args.get('limit') else 20
    if limit > 50:
        limit = 50

    supabase = current_app.config['SUPABASE']
    try:
        query = supabase.table('proveedores').select('id, nombre, rut')
        if term and len(term) >= 1:
            # Buscar por nombre o rut
            query = query.or_(f"nombre.ilike.%{term}%", f"rut.ilike.%{term}%")
        res = query.order('nombre').limit(limit).execute()
        items = res.data or []
        results = [{'value': p.get('id'), 'label': f"{p.get('nombre')} ({p.get('rut')})"} for p in items]
        return jsonify({'results': results})
    except Exception as e:
        current_app.logger.error(f"Error api_buscar proveedores: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno'}), 500
