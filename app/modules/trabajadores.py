# app/modules/trabajadores.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from app.modules.usuarios import require_modulo
import re
import logging

bp = Blueprint("trabajadores", __name__, template_folder="../templates/trabajadores")

def validar_email(email):
    """Valida el formato del email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validar_nombre(nombre):
    """Valida el formato del nombre"""
    if not nombre or len(nombre.strip()) < 2:
        return False, "El nombre debe tener al menos 2 caracteres"
    if len(nombre.strip()) > 100:
        return False, "El nombre no puede exceder 100 caracteres"
    return True, ""

@bp.route("/", methods=["GET"])
@require_modulo('trabajadores')
def list_trabajadores():
    """Lista todos los trabajadores con manejo de errores mejorado"""
    try:
        supabase = current_app.config['SUPABASE']
        
        # Obtener todos los trabajadores ordenados por nombre
        response = supabase.table("trabajadores").select("*").order("nombre").execute()
        
        if hasattr(response, 'error') and response.error:
            current_app.logger.error(f"Error al obtener trabajadores: {response.error}")
            flash("Error al cargar los trabajadores. Intente nuevamente.", "danger")
            trabajadores = []
        else:
            trabajadores = response.data or []
            
        current_app.logger.info(f"Trabajadores cargados: {len(trabajadores)}")
        
        return render_template("trabajadores/form.html", 
                             trabajadores=trabajadores,
                             trabajador=None)
        
    except Exception as e:
        current_app.logger.error(f"Error inesperado al listar trabajadores: {str(e)}")
        flash("Error inesperado al cargar los trabajadores.", "danger")
        return render_template("trabajadores/form.html", 
                             trabajadores=[],
                             trabajador=None)

@bp.route("/new", methods=["POST"])
@require_modulo('trabajadores')
def new_trabajador():
    """Crea un nuevo trabajador con validaciones mejoradas"""
    try:
        supabase = current_app.config['SUPABASE']
        
        # Obtener y limpiar datos del formulario
        nombre = request.form.get("nombre", "").strip().upper()
        correo = request.form.get("correo", "").strip().lower()
        
        current_app.logger.info(f"Creando trabajador: nombre='{nombre}', correo='{correo}'")
        
        # Validaciones
        if not nombre or not correo:
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for("trabajadores.list_trabajadores"))
        
        # Validar nombre
        nombre_valido, nombre_error = validar_nombre(nombre)
        if not nombre_valido:
            flash(nombre_error, "danger")
            return redirect(url_for("trabajadores.list_trabajadores"))
        
        # Validar email
        if not validar_email(correo):
            flash("El formato del correo electrónico no es válido.", "danger")
            return redirect(url_for("trabajadores.list_trabajadores"))
        
        # Verificar duplicado por correo
        dup_response = supabase.table("trabajadores").select("id, nombre").eq("correo", correo).execute()
        
        if hasattr(dup_response, 'error') and dup_response.error:
            current_app.logger.error(f"Error al verificar duplicados: {dup_response.error}")
            flash("Error al verificar duplicados. Intente nuevamente.", "danger")
            return redirect(url_for("trabajadores.list_trabajadores"))
        
        if dup_response.data:
            existing_worker = dup_response.data[0]
            flash(f"El correo ya está registrado para el trabajador: {existing_worker['nombre']}", "danger")
            return redirect(url_for("trabajadores.list_trabajadores"))
        
        # Verificar duplicado por nombre (advertencia, no bloqueo)
        name_dup_response = supabase.table("trabajadores").select("id, correo").eq("nombre", nombre).execute()
        if name_dup_response.data:
            existing_worker = name_dup_response.data[0]
            flash(f"Ya existe un trabajador con el nombre '{nombre}' (correo: {existing_worker['correo']}). Se creará de todas formas.", "warning")
        
        # Crear el trabajador
        payload = {
            "nombre": nombre,
            "correo": correo
        }
        
        insert_response = supabase.table("trabajadores").insert(payload).execute()
        
        if hasattr(insert_response, 'error') and insert_response.error:
            current_app.logger.error(f"Error al crear trabajador: {insert_response.error}")
            flash("Error al crear el trabajador. Intente nuevamente.", "danger")
            return redirect(url_for("trabajadores.list_trabajadores"))
        
        current_app.logger.info(f"Trabajador creado exitosamente: {nombre} ({correo})")
        flash(f"Trabajador '{nombre}' creado exitosamente.", "success")
        return redirect(url_for("trabajadores.list_trabajadores"))
        
    except Exception as e:
        current_app.logger.error(f"Error inesperado al crear trabajador: {str(e)}")
        flash("Error inesperado al crear el trabajador.", "danger")
        return redirect(url_for("trabajadores.list_trabajadores"))

@bp.route("/edit/<int:id>", methods=["GET", "POST"])
@require_modulo('trabajadores')
def edit_trabajador(id):
    """Edita un trabajador existente con validaciones mejoradas"""
    try:
        supabase = current_app.config['SUPABASE']
        
        # Obtener el trabajador actual
        worker_response = supabase.table("trabajadores").select("*").eq("id", id).execute()
        
        if hasattr(worker_response, 'error') and worker_response.error:
            current_app.logger.error(f"Error al obtener trabajador {id}: {worker_response.error}")
            flash("Error al obtener los datos del trabajador.", "danger")
            return redirect(url_for("trabajadores.list_trabajadores"))
        
        trabajador = (worker_response.data or [None])[0]
        if not trabajador:
            flash("Trabajador no encontrado.", "danger")
            return redirect(url_for("trabajadores.list_trabajadores"))
        
        if request.method == "POST":
            # Obtener y limpiar datos del formulario
            nombre_new = request.form.get("nombre", "").strip().upper()
            correo_new = request.form.get("correo", "").strip().lower()
            
            current_app.logger.info(f"Editando trabajador {id}: nombre='{nombre_new}', correo='{correo_new}'")
            
            # Validaciones
            if not nombre_new or not correo_new:
                flash("Todos los campos son obligatorios.", "danger")
                return redirect(url_for("trabajadores.edit_trabajador", id=id))
            
            # Validar nombre
            nombre_valido, nombre_error = validar_nombre(nombre_new)
            if not nombre_valido:
                flash(nombre_error, "danger")
                return redirect(url_for("trabajadores.edit_trabajador", id=id))
            
            # Validar email
            if not validar_email(correo_new):
                flash("El formato del correo electrónico no es válido.", "danger")
                return redirect(url_for("trabajadores.edit_trabajador", id=id))
            
            # Verificar duplicado de correo (solo si cambió)
            if correo_new != trabajador["correo"]:
                dup_response = supabase.table("trabajadores").select("id, nombre").eq("correo", correo_new).execute()
                
                if hasattr(dup_response, 'error') and dup_response.error:
                    current_app.logger.error(f"Error al verificar duplicados: {dup_response.error}")
                    flash("Error al verificar duplicados. Intente nuevamente.", "danger")
                    return redirect(url_for("trabajadores.edit_trabajador", id=id))
                
                if dup_response.data:
                    existing_worker = dup_response.data[0]
                    flash(f"El correo ya está registrado para el trabajador: {existing_worker['nombre']}", "danger")
                    return redirect(url_for("trabajadores.edit_trabajador", id=id))
            
            # Verificar duplicado de nombre (advertencia si cambió)
            if nombre_new != trabajador["nombre"]:
                name_dup_response = supabase.table("trabajadores").select("id, correo").eq("nombre", nombre_new).execute()
                if name_dup_response.data:
                    existing_worker = name_dup_response.data[0]
                    if existing_worker["id"] != id:  # No es el mismo trabajador
                        flash(f"Ya existe un trabajador con el nombre '{nombre_new}' (correo: {existing_worker['correo']}). Se actualizará de todas formas.", "warning")
            
            # Actualizar el trabajador
            payload = {
                "nombre": nombre_new,
                "correo": correo_new
            }
            
            update_response = supabase.table("trabajadores").update(payload).eq("id", id).execute()
            
            if hasattr(update_response, 'error') and update_response.error:
                current_app.logger.error(f"Error al actualizar trabajador {id}: {update_response.error}")
                flash("Error al actualizar el trabajador. Intente nuevamente.", "danger")
                return redirect(url_for("trabajadores.edit_trabajador", id=id))
            
            current_app.logger.info(f"Trabajador {id} actualizado exitosamente: {nombre_new} ({correo_new})")
            flash(f"Trabajador '{nombre_new}' actualizado exitosamente.", "success")
            return redirect(url_for("trabajadores.list_trabajadores"))
        
        # GET: Mostrar formulario de edición
        trabajadores_response = supabase.table("trabajadores").select("*").order("nombre").execute()
        trabajadores = trabajadores_response.data or []
        
        return render_template("trabajadores/form.html",
                             trabajadores=trabajadores,
                             trabajador=trabajador)
        
    except Exception as e:
        current_app.logger.error(f"Error inesperado al editar trabajador {id}: {str(e)}")
        flash("Error inesperado al editar el trabajador.", "danger")
        return redirect(url_for("trabajadores.list_trabajadores"))

@bp.route("/api/export", methods=["GET"])
@require_modulo('trabajadores')
def export_trabajadores():
    """Exporta la lista de trabajadores (funcionalidad futura)"""
    flash("Funcionalidad de exportación próximamente disponible.", "info")
    return redirect(url_for("trabajadores.list_trabajadores"))