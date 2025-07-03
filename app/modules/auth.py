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
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.get_by_email(email)
        if not user:
            flash('Usuario no encontrado', 'warning')
        elif not check_password_hash(user.password, password):
            flash('Contraseña incorrecta', 'danger')
        else:
            login_user(user)
            flash(f'Bienvenido, {user.nombre}', 'success')
            
            from app.modules.usuarios import get_modulos_usuario
            modulos = get_modulos_usuario()
            # Mapea nombres de módulo a endpoint
            modulo_to_endpoint = {
                'orden_de_pago': 'ordenes_pago.list_ordenes_pago',
                'ingresos': 'ingresos.list_ingresos',
                'materiales': 'materiales.list_materiales',
                'proveedores': 'proveedores.list_proveedores',
                'trabajadores': 'trabajadores.list_trabajadores',
                'proyectos': 'proyectos.list_proyectos',
                'item': 'items.list_items',
                'pagos': 'pagos.list_pagos',
                'presupuesto': 'presupuestos.form_presupuesto',
                # ...agrega los que correspondan...
            }
            for modulo in modulos:
                if modulo in modulo_to_endpoint:
                    return redirect(url_for(modulo_to_endpoint[modulo]))
            # Si no tiene ningún permiso, redirige a una página de "sin permisos"
            return redirect(url_for('sin_permisos'))
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