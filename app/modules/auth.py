from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user

bp_auth = Blueprint('auth', __name__, template_folder='../templates/auth')

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

class User(UserMixin):
    def __init__(self, id, nombre, email, password, is_admin):
        self.id = id
        self.nombre = nombre
        self.email = email
        self.password = password
        # Normalize is_admin to a real boolean
        if isinstance(is_admin, str):
            self.is_admin = is_admin.lower() == "true"
        else:
            self.is_admin = bool(is_admin)

    @staticmethod
    def get_by_email(email):
        supabase = current_app.config['SUPABASE']
        res = supabase.table('usuarios').select('*').eq('email', email).limit(1).execute()
        data = res.data
        if data:
            u = data[0]
            return User(u['id'], u['nombre'], u['email'], u['password'], u.get('is_admin', False))
        return None

    @staticmethod
    def get_by_id(user_id):
        supabase = current_app.config['SUPABASE']
        res = supabase.table('usuarios').select('*').eq('id', user_id).limit(1).execute()
        data = res.data
        if data:
            u = data[0]
            return User(u['id'], u['nombre'], u['email'], u['password'], u.get('is_admin', False))
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

@bp_auth.route('/login', methods=['GET', 'POST'])
def login():
    from werkzeug.security import check_password_hash
    from flask import jsonify

    def wants_json():
        # Detectar peticiones AJAX o que acepten JSON
        accept = request.headers.get('Accept', '')
        xrw = request.headers.get('X-Requested-With', '')
        return 'application/json' in accept or xrw == 'XMLHttpRequest'
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.get_by_email(email)
        if not user:
            if wants_json():
                return jsonify(success=False, message='Usuario no encontrado'), 400
            flash('Usuario no encontrado', 'warning')
        elif not check_password_hash(user.password, password):
            if wants_json():
                return jsonify(success=False, message='Contraseña incorrecta'), 401
            flash('Contraseña incorrecta', 'danger')
        else:
            login_user(user)
            
            # Verificar si tiene contraseña temporal
            supabase = current_app.config['SUPABASE']
            usuario_data = supabase.table('usuarios').select('motivo_bloqueo').eq('id', user.id).single().execute().data
            
            current_app.logger.info(f"Usuario {user.id} logueado. Motivo bloqueo: {usuario_data.get('motivo_bloqueo') if usuario_data else 'None'}")
            
            if usuario_data and usuario_data.get('motivo_bloqueo') == 'CONTRASEÑA_TEMPORAL':
                current_app.logger.info(f"Usuario {user.id} tiene contraseña temporal, redirigiendo a cambio de contraseña")
                if wants_json():
                    return jsonify(success=True, redirect=url_for('usuarios.change_password'), notice='Debes cambiar tu contraseña temporal antes de continuar')
                flash('Debes cambiar tu contraseña temporal antes de continuar', 'warning')
                return redirect(url_for('usuarios.change_password'))
            
            # Determinar primer módulo permitido
            from app.modules.usuarios import get_modulos_usuario
            modulos = get_modulos_usuario()
            # Orden de prioridad de módulos (ajustar según tu app)
            modulo_rutas = [
                ('usuarios', 'usuarios.list_usuarios'),
                ('ordenes', 'ordenes.new_orden'),
                ('ingresos', 'ingresos.list_ingresos'),
                ('ordenes_pago', 'ordenes_pago.list_ordenes_pago'),
                ('ordenes_pago_pendientes', 'ordenes_pago_pendientes.list_pendientes'),
                ('pagos', 'pagos.list_pagos'),
                ('proveedores', 'proveedores.list_proveedores'),
                ('materiales', 'materiales.list_materiales'),
                ('items', 'items.list_items'),
                ('trabajadores', 'trabajadores.list_trabajadores'),
                ('proyectos', 'proyectos.list_proyectos'),
                ('presupuestos', 'presupuestos.form_presupuesto'),
                ('gastos_directos', 'gastos_directos.form_gastos_directos'),
                ('estado_presupuesto', 'estado_presupuesto.show_estado'),
            ]
            redirect_url = None
            for modulo, endpoint in modulo_rutas:
                if modulo in modulos:
                    redirect_url = url_for(endpoint)
                    break
            if not redirect_url:
                # Si no tiene acceso a ningún módulo conocido, cerrar sesión y mostrar error
                if wants_json():
                    logout_user()
                    return jsonify(success=False, message='No tienes acceso a ningún módulo. Contacta al administrador.'), 403
                flash('No tienes acceso a ningún módulo. Contacta al administrador.', 'danger')
                return redirect(url_for('auth.logout'))

            if wants_json():
                return jsonify(success=True, redirect=redirect_url, message=f'Bienvenido, {user.nombre}')

            flash(f'Bienvenido, {user.nombre}', 'success')
    return render_template('auth/login.html')

@bp_auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('auth.login'))

@bp_auth.route('/sin_permisos')
def sin_permisos():
    return render_template('sin_permisos.html')
