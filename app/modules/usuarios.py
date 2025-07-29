
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, get_flashed_messages
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, date
import secrets
import string
import logging

def get_modulos_usuario():
    from flask_login import current_user
    if not current_user.is_authenticated:
        return []
    supabase = current_app.config['SUPABASE']
    rows = supabase.table('usuario_modulo').select('modulo_id,modulos(nombre_modulo)').eq('usuario_id', current_user.id).execute().data
    return [row['modulos']['nombre_modulo'] for row in rows]

def require_modulo(nombre_modulo):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            # get_modulos_usuario ya está definido arriba
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes['application/json'] > 0
            if not current_user.is_authenticated:
                if is_ajax:
                    return jsonify(success=False, error='Debes iniciar sesión para acceder a este módulo.'), 401
                flash('Debes iniciar sesión para acceder a este módulo.', 'warning')
                return redirect(url_for('auth.login'))
            modulos_usuario = [m.strip().lower() for m in get_modulos_usuario()]
            if nombre_modulo.strip().lower() not in modulos_usuario:
                return render_template('sin_permisos.html'), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

bp = Blueprint('usuarios', __name__, template_folder='../templates/usuarios')

@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@require_modulo('Usuarios')
def nuevo_usuario():
    supabase = current_app.config['SUPABASE']
    
    # Obtener módulos disponibles
    try:
        def fetch_all_rows(table, select_str, order_col=None, desc=False):
            page_size = 1000
            offset = 0
            all_rows = []
            while True:
                q = supabase.table(table).select(select_str)
                if order_col:
                    q = q.order(order_col, desc=desc)
                q = q.range(offset, offset + page_size - 1)
                batch = q.execute().data or []
                all_rows.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size
            return all_rows

        modulos = fetch_all_rows('modulos', '*', 'nombre_modulo')
        current_app.logger.info(f"Módulos obtenidos: {len(modulos) if modulos else 0}")
        if modulos:
            current_app.logger.info(f"Primer módulo: {modulos[0]}")
    except Exception as e:
        current_app.logger.error(f"Error obteniendo módulos: {e}")
        modulos = []

    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            activo = request.form.get('activo', 'on') == 'on'
            modulos_seleccionados = request.form.getlist('modulos')

            current_app.logger.info(f"Creando usuario: {nombre} ({email})")
            current_app.logger.info(f"Módulos seleccionados: {modulos_seleccionados}")

            # Validaciones básicas
            if not nombre or not email or not password:
                flash('Todos los campos son requeridos', 'danger')
                return render_template('usuarios/nuevo.html', modulos=modulos)

            if len(password) < 8:
                flash('La contraseña debe tener al menos 8 caracteres', 'danger')
                return render_template('usuarios/nuevo.html', modulos=modulos)

            if not modulos_seleccionados:
                flash('Debe seleccionar al menos un módulo', 'danger')
                return render_template('usuarios/nuevo.html', modulos=modulos)

            # Verificar si el email ya existe
            try:
                existe = supabase.table('usuarios').select('id').eq('email', email).execute().data
                if existe:
                    flash('Ya existe un usuario con este email.', 'danger')
                    return render_template('usuarios/nuevo.html', modulos=modulos)
            except Exception as e:
                current_app.logger.error(f"Error verificando email existente: {e}")

            # Crear usuario
            hashed = generate_password_hash(password)
            user_data = {
                'nombre': nombre,
                'email': email,
                'password': hashed,
                'activo': activo,
                'bloqueado': False,
                'intentos_fallidos': 0,
                'fecha_creacion': datetime.now().isoformat()
            }
            
            current_app.logger.info(f"Insertando usuario: {user_data}")
            
            res = supabase.table('usuarios').insert(user_data).execute()
            
            current_app.logger.info(f"Respuesta Supabase usuarios: {res}")
            
            if res.data:
                usuario_id = res.data[0]['id']
                current_app.logger.info(f"Usuario creado con ID: {usuario_id}")
                
                # Insertar módulos seleccionados
                modulos_insertados = 0
                for modulo_id in modulos_seleccionados:
                    try:
                        current_app.logger.info(f"Insertando en usuario_modulo: {usuario_id}, {modulo_id}")
                        res_mod = supabase.table('usuario_modulo').insert({
                            'usuario_id': int(usuario_id),
                            'modulo_id': int(modulo_id)
                        }).execute()
                        current_app.logger.info(f"Respuesta usuario_modulo: {res_mod}")
                        modulos_insertados += 1
                    except Exception as e:
                        current_app.logger.error(f"Error insertando módulo {modulo_id}: {e}")
                
                current_app.logger.info(f"Módulos insertados: {modulos_insertados}")
                
                flash(f'Usuario creado correctamente con {modulos_insertados} módulos asignados', 'success')
                return redirect(url_for('usuarios.list_usuarios'))
            else:
                error_msg = f'Error al crear usuario: {res}'
                current_app.logger.error(error_msg)
                flash(error_msg, 'danger')
                return render_template('usuarios/nuevo.html', modulos=modulos)
                
        except Exception as e:
            error_msg = f'Error inesperado: {str(e)}'
            current_app.logger.error(error_msg)
            flash(error_msg, 'danger')
            return render_template('usuarios/nuevo.html', modulos=modulos)

    return render_template('usuarios/nuevo.html', modulos=modulos)

@bp.route('/listado')
@login_required
@require_modulo('Usuarios')
def list_usuarios():
    supabase = current_app.config['SUPABASE']
    
    # Obtener parámetros de filtro
    filtro_estado = request.args.get('estado', 'todos')
    buscar = request.args.get('buscar', '')
    
    # Consulta base
    query = supabase.table('usuarios').select('id, nombre, email, activo, bloqueado, fecha_creacion, fecha_ultimo_acceso, intentos_fallidos')
    
    # Aplicar filtros
    if filtro_estado == 'activos':
        query = query.eq('activo', True)
    elif filtro_estado == 'inactivos':
        query = query.eq('activo', False)
    elif filtro_estado == 'bloqueados':
        query = query.eq('bloqueado', True)
    
    if buscar:
        query = query.or_(f'nombre.ilike.%{buscar}%,email.ilike.%{buscar}%')
    
    usuarios = query.order('nombre').execute().data or []
    
    # Obtener estadísticas
    stats = {
        'total': len(usuarios),
        'activos': len([u for u in usuarios if u.get('activo', True)]),
        'inactivos': len([u for u in usuarios if not u.get('activo', True)]),
        'bloqueados': len([u for u in usuarios if u.get('bloqueado', False)])
    }
    
    # Obtener módulos de cada usuario para mostrar en la tabla
    for usuario in usuarios:
        modulos = supabase.table('usuario_modulo').select('modulo_id,modulos(nombre_modulo)').eq('usuario_id', usuario['id']).execute().data or []
        usuario['modulos'] = [m['modulos']['nombre_modulo'] for m in modulos]
    
    return render_template('usuarios/listado.html', 
                         usuarios=usuarios, 
                         stats=stats, 
                         filtro_estado=filtro_estado,
                         buscar=buscar)

def get_modulos_usuario():
    from flask_login import current_user
    if not current_user.is_authenticated:
        return []
    
    supabase = current_app.config['SUPABASE']
    # Obtiene los módulos permitidos para el usuario actual
    rows = supabase.table('usuario_modulo').select('modulo_id,modulos(nombre_modulo)').eq('usuario_id', current_user.id).execute().data
    return [row['modulos']['nombre_modulo'] for row in rows]

def validar_password(password):
    """Valida que la contraseña tenga al menos 8 caracteres, una mayúscula, una minúscula y un número."""
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True

def generar_password_temporal():
    """Genera una contraseña temporal segura."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(12))

def actualizar_ultimo_acceso(usuario_id):
    """Actualiza la fecha de último acceso del usuario."""
    try:
        supabase = current_app.config['SUPABASE']
        supabase.table('usuarios').update({
            'fecha_ultimo_acceso': datetime.now().isoformat()
        }).eq('id', usuario_id).execute()
    except Exception as e:
        current_app.logger.error(f"Error al actualizar último acceso: {e}")

def require_modulo(nombre_modulo):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            from app.modules.usuarios import get_modulos_usuario

            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes['application/json'] > 0

            # Verificar que el usuario esté autenticado
            if not current_user.is_authenticated:
                if is_ajax:
                    return jsonify(success=False, error='Debes iniciar sesión para acceder a este módulo.'), 401
                flash('Debes iniciar sesión para acceder a este módulo.', 'warning')
                return redirect(url_for('auth.login'))

            if nombre_modulo not in get_modulos_usuario():
                # Mostrar la página elegante de acceso denegado siempre
                return render_template('sin_permisos.html'), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@bp.route('/toggle_modulo_permiso', methods=['POST'])
@login_required
def toggle_modulo_permiso():
    data = request.get_json()
    usuario_id = int(data.get('usuario_id'))
    modulo_id = int(data.get('modulo_id'))
    permitir = data.get('permitir')

    supabase = current_app.config['SUPABASE']

    # Verifica si ya existe el permiso
    existe = supabase.table('usuario_modulo') \
        .select('id') \
        .eq('usuario_id', usuario_id) \
        .eq('modulo_id', modulo_id) \
        .execute().data

    if permitir:
        if not existe:
            # Agregar permiso
            supabase.table('usuario_modulo').insert({
                'usuario_id': usuario_id,
                'modulo_id': modulo_id
            }).execute()
            return jsonify(success=True, message="Permiso otorgado.")
        else:
            return jsonify(success=True, message="El permiso ya existía.")
    else:
        if existe:
            # Quitar permiso
            supabase.table('usuario_modulo') \
                .delete() \
                .eq('usuario_id', usuario_id) \
                .eq('modulo_id', modulo_id) \
                .execute()
            return jsonify(success=True, message="Permiso revocado.")
        else:
            return jsonify(success=True, message="El permiso ya estaba revocado.")

    return jsonify(success=False, message="Error inesperado.")

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    supabase = current_app.config['SUPABASE']

    # Obtener usuario
    usuario = supabase.table('usuarios').select('*').eq('id', id).single().execute().data
    if not usuario:
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('usuarios.list_usuarios'))

    # Obtener todos los módulos
    modulos = supabase.table('modulos').select('*').execute().data or []

    # Obtener módulos a los que el usuario tiene acceso
    permisos = supabase.table('usuario_modulo').select('modulo_id').eq('usuario_id', id).execute().data or []
    modulos_usuario = {int(p['modulo_id']) for p in permisos}

    # Permitir acceso solo si el usuario actual tiene acceso al módulo Usuarios
    modulos_actual = [m.strip().lower() for m in get_modulos_usuario()]
    if 'usuarios' not in modulos_actual:
        return render_template('sin_permisos.html'), 403

    # Actualizar datos básicos del usuario (nombre/email)
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        supabase.table('usuarios').update({'nombre': nombre, 'email': email}).eq('id', id).execute()
        flash('Datos actualizados', 'success')
        return redirect(url_for('usuarios.editar_usuario', id=id))

    return render_template(
        'usuarios/editar.html',
        usuario=usuario,
        modulos=modulos,
        modulos_usuario=modulos_usuario
    )

@bp.route('/toggle_estado/<int:id>', methods=['POST'])
@login_required
def toggle_estado_usuario(id):
    """Activa o desactiva un usuario."""
    supabase = current_app.config['SUPABASE']
    data = request.get_json()
    nuevo_estado = data.get('activo', True)
    
    # Obtener usuario actual
    usuario = supabase.table('usuarios').select('nombre, activo').eq('id', id).single().execute().data
    if not usuario:
        return jsonify(success=False, message="Usuario no encontrado")
    
    # Actualizar estado
    supabase.table('usuarios').update({'activo': nuevo_estado}).eq('id', id).execute()
    
    # Log de auditoría
    accion = f"Usuario {'activado' if nuevo_estado else 'desactivado'}: {usuario['nombre']}"
    current_app.logger.info(accion)
    
    return jsonify(success=True, message=f"Usuario {'activado' if nuevo_estado else 'desactivado'} correctamente")

@bp.route('/toggle_bloqueo/<int:id>', methods=['POST'])
@login_required
def toggle_bloqueo_usuario(id):
    """Bloquea o desbloquea un usuario."""
    supabase = current_app.config['SUPABASE']
    data = request.get_json()
    bloqueado = data.get('bloqueado', False)
    
    # Obtener usuario actual
    usuario = supabase.table('usuarios').select('nombre, bloqueado').eq('id', id).single().execute().data
    if not usuario:
        return jsonify(success=False, message="Usuario no encontrado")
    
    # Actualizar estado de bloqueo y resetear intentos fallidos
    supabase.table('usuarios').update({
        'bloqueado': bloqueado,
        'intentos_fallidos': 0 if not bloqueado else usuario.get('intentos_fallidos', 0)
    }).eq('id', id).execute()
    
    # Log de auditoría
    accion = f"Usuario {'bloqueado' if bloqueado else 'desbloqueado'}: {usuario['nombre']}"
    current_app.logger.info(accion)
    
    return jsonify(success=True, message=f"Usuario {'bloqueado' if bloqueado else 'desbloqueado'} correctamente")

@bp.route('/reset_password/<int:id>', methods=['POST'])
@login_required
def reset_password_usuario(id):
    """Genera una contraseña temporal para el usuario."""
    supabase = current_app.config['SUPABASE']
    
    # Obtener usuario
    usuario = supabase.table('usuarios').select('nombre, email').eq('id', id).single().execute().data
    if not usuario:
        return jsonify(success=False, message="Usuario no encontrado")
    
    # Generar contraseña temporal
    password_temp = generar_password_temporal()
    hashed = generate_password_hash(password_temp)
    
    # Actualizar contraseña y marcar como temporal usando motivo_bloqueo
    supabase.table('usuarios').update({
        'password': hashed,
        'intentos_fallidos': 0,
        'bloqueado': False,
        'motivo_bloqueo': 'CONTRASEÑA_TEMPORAL'
    }).eq('id', id).execute()
    
    # Log de auditoría
    current_app.logger.info(f"Contraseña restablecida para usuario: {usuario['nombre']}")
    
    return jsonify(success=True, message="Contraseña restablecida", password_temp=password_temp)

@bp.route('/dashboard')
@login_required
@require_modulo('Usuarios')
def dashboard_usuarios():
    """Dashboard con estadísticas de usuarios."""
    supabase = current_app.config['SUPABASE']
    
    try:
        # Obtener todos los usuarios
        usuarios = supabase.table('usuarios').select('*').execute().data or []
        
        # Calcular estadísticas de forma segura
        stats = {
            'total_usuarios': len(usuarios),
            'activos': len([u for u in usuarios if u.get('activo', True)]),
            'inactivos': len([u for u in usuarios if not u.get('activo', True)]),
            'bloqueados': len([u for u in usuarios if u.get('bloqueado', False)]),
            'con_intentos_fallidos': len([u for u in usuarios if u.get('intentos_fallidos', 0) > 0])
        }
        
        # Usuarios con más intentos fallidos
        usuarios_riesgo = sorted(
            [u for u in usuarios if u.get('intentos_fallidos', 0) > 0],
            key=lambda x: x.get('intentos_fallidos', 0),
            reverse=True
        )[:5]
        
        # Usuarios inactivos (sin acceso reciente)
        usuarios_inactivos = [u for u in usuarios if not u.get('fecha_ultimo_acceso')]
        
        return render_template('usuarios/dashboard.html', 
                             stats=stats, 
                             usuarios_riesgo=usuarios_riesgo,
                             usuarios_inactivos=usuarios_inactivos)
    except Exception as e:
        current_app.logger.error(f"Error en dashboard_usuarios: {e}")
        flash(f'Error al cargar el dashboard: {str(e)}', 'danger')
        return redirect(url_for('usuarios.list_usuarios'))

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Permite al usuario cambiar su contraseña temporal."""
    # Limpiar mensajes flash previos en GET
    if request.method == 'GET':
        # Consumir mensajes flash para limpiar cualquier mensaje anterior
        list(get_flashed_messages())
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validaciones
        if not current_password or not new_password or not confirm_password:
            flash('Todos los campos son requeridos', 'danger')
            return render_template('usuarios/change_password.html')
        
        if new_password != confirm_password:
            flash('Las contraseñas no coinciden', 'danger')
            return render_template('usuarios/change_password.html')
        
        if len(new_password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres', 'danger')
            return render_template('usuarios/change_password.html')
        
        # Verificar contraseña actual
        supabase = current_app.config['SUPABASE']
        usuario = supabase.table('usuarios').select('password').eq('id', current_user.id).single().execute().data
        
        if not usuario or not check_password_hash(usuario['password'], current_password):
            flash('Contraseña actual incorrecta', 'danger')
            return render_template('usuarios/change_password.html')
        
        # Actualizar contraseña
        try:
            hashed_new = generate_password_hash(new_password)
            
            # Log antes del update
            current_app.logger.info(f"Iniciando actualización de contraseña para usuario: {current_user.id}")
            
            result = supabase.table('usuarios').update({
                'password': hashed_new,
                'motivo_bloqueo': None  # Limpiar la marca de contraseña temporal
            }).eq('id', current_user.id).execute()
            
            # Verificar que la actualización fue exitosa
            if result.data:
                current_app.logger.info(f"Contraseña cambiada exitosamente para usuario: {current_user.nombre}")
                flash('Contraseña actualizada correctamente', 'success')
                
                # Verificar que la nueva contraseña funciona
                usuario_verificar = supabase.table('usuarios').select('password').eq('id', current_user.id).single().execute().data
                if usuario_verificar and check_password_hash(usuario_verificar['password'], new_password):
                    current_app.logger.info(f"Verificación exitosa: Nueva contraseña funciona para usuario: {current_user.id}")
                    return redirect(url_for('main.home'))
                else:
                    current_app.logger.error(f"Error en verificación: Nueva contraseña no funciona para usuario: {current_user.id}")
                    flash('Error en la verificación de la nueva contraseña', 'danger')
                    return render_template('usuarios/change_password.html')
            else:
                current_app.logger.error(f"No se recibieron datos del update para usuario: {current_user.id}")
                flash('Error al actualizar la contraseña en la base de datos', 'danger')
                return render_template('usuarios/change_password.html')
            
        except Exception as e:
            current_app.logger.error(f"Excepción al cambiar contraseña para usuario {current_user.id}: {str(e)}")
            flash('Error al actualizar la contraseña', 'danger')
            return render_template('usuarios/change_password.html')
    
    return render_template('usuarios/change_password.html')

@bp.route('/check_temp_password')
@login_required
def check_temp_password():
    """Verifica si el usuario tiene una contraseña temporal."""
    supabase = current_app.config['SUPABASE']
    usuario = supabase.table('usuarios').select('motivo_bloqueo').eq('id', current_user.id).single().execute().data
    
    if usuario and usuario.get('motivo_bloqueo') == 'CONTRASEÑA_TEMPORAL':
        return jsonify(temp_password=True)
    return jsonify(temp_password=False)

