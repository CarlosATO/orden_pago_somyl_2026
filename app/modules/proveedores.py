from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from app.modules.usuarios import require_modulo
import logging
import re

bp = Blueprint("proveedores", __name__, template_folder="../templates/proveedores")

def validate_rut(rut):
    """Valida formato y dígito verificador del RUT chileno"""
    if not rut:
        return False, "RUT es requerido"
    
    # Limpiar y normalizar
    rut = rut.strip().upper().replace(".", "")
    
    # Verificar formato
    if not re.match(r'^\d{7,8}-[0-9K]$', rut):
        return False, "Formato de RUT inválido. Use: 12345678-9"
    
    # Separar número y dígito verificador
    try:
        num, dv = rut.split('-')
        num = int(num)
    except (ValueError, IndexError):
        return False, "RUT inválido"
    
    # Calcular dígito verificador
    sum_val = 0
    mul = 2
    for digit in reversed(str(num)):
        sum_val += int(digit) * mul
        mul = 7 if mul == 6 else mul + 1
    
    remainder = sum_val % 11
    expected_dv = '0' if remainder == 11 else 'K' if remainder == 10 else str(11 - remainder)
    
    if dv != expected_dv:
        return False, "Dígito verificador incorrecto"
    
    return True, rut

def normalize_data(data):
    """Normaliza los datos del proveedor"""
    normalized = {}
    
    # Campos que van en mayúsculas
    uppercase_fields = ['nombre', 'direccion', 'comuna', 'fono', 'contacto', 'banco', 'cuenta', 'paguese_a']
    
    for field in uppercase_fields:
        value = data.get(field, '').strip()
        normalized[field] = value.upper() if value else ''
    
    # Campos especiales
    normalized['correo'] = data.get('correo', '').strip().lower()
    normalized['rut'] = data.get('rut', '').strip().upper()
    
    return normalized

@bp.route("/", methods=["GET"])
@require_modulo('proveedores')
def list_proveedores():
    """Lista todos los proveedores con manejo de errores mejorado"""
    try:
        supabase = current_app.config['SUPABASE']
        
        response = supabase.table("proveedores").select("*").order("nombre").execute()
        
        if hasattr(response, 'error') and response.error:
            current_app.logger.error(f"Error al obtener proveedores: {response.error}")
            flash("Error al cargar los proveedores", "danger")
            proveedores = []
        else:
            proveedores = response.data or []
            
        current_app.logger.info(f"Cargados {len(proveedores)} proveedores")
        
        return render_template("proveedores/form.html", proveedores=proveedores)
        
    except Exception as e:
        current_app.logger.error(f"Error inesperado al listar proveedores: {str(e)}")
        flash("Error inesperado al cargar los proveedores", "danger")
        return render_template("proveedores/form.html", proveedores=[])

@bp.route("/new", methods=["POST"])
@require_modulo('proveedores')
def new_proveedor():
    """Crea un nuevo proveedor con validaciones mejoradas"""
    try:
        supabase = current_app.config['SUPABASE']
        
        # Normalizar datos
        data = normalize_data(request.form)
        
        # Validar RUT
        is_valid, rut_result = validate_rut(data['rut'])
        if not is_valid:
            flash(f"Error en RUT: {rut_result}", "danger")
            return redirect(url_for("proveedores.list_proveedores"))
        
        data['rut'] = rut_result
        
        # Validar campos requeridos
        if not data['nombre']:
            flash("El nombre/razón social es requerido", "danger")
            return redirect(url_for("proveedores.list_proveedores"))
        
        # Verificar duplicado por RUT
        existing = supabase.table("proveedores").select("id, nombre").eq("rut", data['rut']).execute()
        
        if existing.data:
            flash(f"Ya existe un proveedor con RUT {data['rut']}: {existing.data[0]['nombre']}", "danger")
            return redirect(url_for("proveedores.list_proveedores"))
        
        # Verificar duplicado por nombre
        existing_name = supabase.table("proveedores").select("id, rut").eq("nombre", data['nombre']).execute()
        
        if existing_name.data:
            flash(f"Ya existe un proveedor con el nombre '{data['nombre']}'", "warning")
        
        # Insertar nuevo proveedor
        result = supabase.table("proveedores").insert(data).execute()
        
        if hasattr(result, 'error') and result.error:
            current_app.logger.error(f"Error al crear proveedor: {result.error}")
            flash("Error al crear el proveedor", "danger")
        else:
            current_app.logger.info(f"Proveedor creado: {data['nombre']} - {data['rut']}")
            flash(f"Proveedor '{data['nombre']}' creado exitosamente", "success")
        
        return redirect(url_for("proveedores.list_proveedores"))
        
    except Exception as e:
        current_app.logger.error(f"Error inesperado al crear proveedor: {str(e)}")
        flash("Error inesperado al crear el proveedor", "danger")
        return redirect(url_for("proveedores.list_proveedores"))

@bp.route("/edit/<int:id>", methods=["GET", "POST"])
@require_modulo('proveedores')
def edit_proveedor(id):
    """Edita un proveedor existente con validaciones mejoradas"""
    try:
        supabase = current_app.config['SUPABASE']
        
        # Obtener proveedor actual
        response = supabase.table("proveedores").select("*").eq("id", id).execute()
        
        if not response.data:
            flash("Proveedor no encontrado", "danger")
            return redirect(url_for("proveedores.list_proveedores"))
        
        proveedor = response.data[0]
        
        if request.method == "POST":
            # Normalizar datos
            data = normalize_data(request.form)
            
            # Validar RUT
            is_valid, rut_result = validate_rut(data['rut'])
            if not is_valid:
                flash(f"Error en RUT: {rut_result}", "danger")
                # Retornar al formulario con datos
                proveedores = supabase.table("proveedores").select("*").order("nombre").execute().data or []
                return render_template("proveedores/form.html", proveedores=proveedores, proveedor=proveedor)
            
            data['rut'] = rut_result
            
            # Validar campos requeridos
            if not data['nombre']:
                flash("El nombre/razón social es requerido", "danger")
                proveedores = supabase.table("proveedores").select("*").order("nombre").execute().data or []
                return render_template("proveedores/form.html", proveedores=proveedores, proveedor=proveedor)
            
            # Verificar duplicado de RUT (solo si cambió)
            if data['rut'] != proveedor['rut']:
                existing = supabase.table("proveedores").select("id, nombre").eq("rut", data['rut']).execute()
                if existing.data:
                    flash(f"Ya existe otro proveedor con RUT {data['rut']}: {existing.data[0]['nombre']}", "danger")
                    proveedores = supabase.table("proveedores").select("*").order("nombre").execute().data or []
                    return render_template("proveedores/form.html", proveedores=proveedores, proveedor=proveedor)
            
            # Verificar duplicado de nombre (solo si cambió)
            if data['nombre'] != proveedor['nombre']:
                existing_name = supabase.table("proveedores").select("id, rut").eq("nombre", data['nombre']).execute()
                if existing_name.data:
                    flash(f"Ya existe otro proveedor con el nombre '{data['nombre']}'", "warning")
            
            # Actualizar proveedor
            result = supabase.table("proveedores").update(data).eq("id", id).execute()
            
            if hasattr(result, 'error') and result.error:
                current_app.logger.error(f"Error al actualizar proveedor: {result.error}")
                flash("Error al actualizar el proveedor", "danger")
            else:
                current_app.logger.info(f"Proveedor actualizado: {data['nombre']} - {data['rut']}")
                flash(f"Proveedor '{data['nombre']}' actualizado exitosamente", "success")
            
            return redirect(url_for("proveedores.list_proveedores"))
        
        # GET: mostrar formulario de edición
        proveedores = supabase.table("proveedores").select("*").order("nombre").execute().data or []
        return render_template("proveedores/form.html", proveedores=proveedores, proveedor=proveedor)
        
    except Exception as e:
        current_app.logger.error(f"Error inesperado al editar proveedor {id}: {str(e)}")
        flash("Error inesperado al editar el proveedor", "danger")
        return redirect(url_for("proveedores.list_proveedores"))

@bp.route("/api/search", methods=["GET"])
@require_modulo('proveedores')
def api_search_proveedores():
    """API para búsqueda de proveedores (para Select2 u otros componentes)"""
    try:
        supabase = current_app.config['SUPABASE']
        term = request.args.get('term', '').strip()
        
        if not term:
            return jsonify({"results": []})
        
        # Buscar por nombre o RUT
        proveedores = supabase.table("proveedores") \
            .select("id, nombre, rut") \
            .or_(f"nombre.ilike.%{term}%,rut.ilike.%{term}%") \
            .limit(20) \
            .execute().data or []
        
        results = [
            {
                "id": p["id"], 
                "text": f"{p['nombre']} - {p['rut']}", 
                "nombre": p["nombre"],
                "rut": p["rut"]
            } 
            for p in proveedores
        ]
        
        return jsonify({"results": results})
        
    except Exception as e:
        current_app.logger.error(f"Error en búsqueda de proveedores: {str(e)}")
        return jsonify({"results": [], "error": "Error en la búsqueda"})

@bp.route("/api/validate_rut", methods=["POST"])
@require_modulo('proveedores')
def api_validate_rut():
    """API para validar RUT"""
    try:
        data = request.get_json()
        rut = data.get('rut', '')
        current_id = data.get('current_id')  # Para edición
        
        is_valid, result = validate_rut(rut)
        
        if not is_valid:
            return jsonify({"valid": False, "message": result})
        
        # Verificar si ya existe
        supabase = current_app.config['SUPABASE']
        query = supabase.table("proveedores").select("id, nombre").eq("rut", result)
        
        if current_id:
            query = query.neq("id", current_id)
        
        existing = query.execute().data
        
        if existing:
            return jsonify({
                "valid": False, 
                "message": f"RUT ya registrado para: {existing[0]['nombre']}"
            })
        
        return jsonify({"valid": True, "formatted_rut": result})
        
    except Exception as e:
        current_app.logger.error(f"Error validando RUT: {str(e)}")
        return jsonify({"valid": False, "message": "Error en validación"})