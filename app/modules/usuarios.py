from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from werkzeug.security import generate_password_hash
from flask_login import login_required, current_user
from functools import wraps

bp = Blueprint('usuarios', __name__, template_folder='../templates/usuarios')

@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_usuario():
    supabase = current_app.config['SUPABASE']
    modulos = supabase.table('modulos').select('*').execute().data

    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        modulos_seleccionados = request.form.getlist('modulos')

        hashed = generate_password_hash(password)
        res = supabase.table('usuarios').insert({
            'nombre': nombre,
            'email': email,
            'password': hashed
        }).execute()
        print("Respuesta Supabase usuarios:", res)
        if res.data:
            usuario_id = res.data[0]['id']
            # Solo intenta insertar si hay módulos seleccionados
            for modulo_id in modulos_seleccionados:
                try:
                    print("Insertando en usuario_modulo:", int(usuario_id), int(modulo_id))
                    res_mod = supabase.table('usuario_modulo').insert({
                        'usuario_id': int(usuario_id),
                        'modulo_id': int(modulo_id)
                    }).execute()
                    print("Respuesta usuario_modulo:", res_mod)
                except Exception as e:
                    print("Error insertando en usuario_modulo:", e)
            flash('Usuario creado correctamente', 'success')
            return redirect(url_for('usuarios.list_usuarios'))
        else:
            flash(f'Error al crear usuario: {res}', 'danger')

    return render_template('usuarios/nuevo.html', modulos=modulos)

@bp.route('/listado')
@login_required
def list_usuarios():
    supabase = current_app.config['SUPABASE']
    # Obtener lista de usuarios
    usuarios = supabase.table('usuarios').select('*').execute().data
    return render_template('usuarios/listado.html', usuarios=usuarios)

def get_modulos_usuario():
    supabase = current_app.config['SUPABASE']
    # Obtiene los módulos permitidos para el usuario actual
    rows = supabase.table('usuario_modulo').select('modulo_id,modulos(nombre_modulo)').eq('usuario_id', current_user.id).execute().data
    return [row['modulos']['nombre_modulo'] for row in rows]

def require_modulo(nombre_modulo):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from app.modules.usuarios import get_modulos_usuario
            if nombre_modulo not in get_modulos_usuario():
                flash('No tienes permiso para acceder a este módulo.', 'danger')
                return redirect(url_for('auth.sin_permisos'))
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

