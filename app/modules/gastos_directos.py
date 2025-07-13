from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from app.modules.usuarios import require_modulo
from app.utils.static_data import get_cached_proyectos_with_id, get_cached_items_with_id
from datetime import date, datetime
import logging

bp_gastos_directos = Blueprint("gastos_directos", __name__, url_prefix="/gastos_directos")

@bp_gastos_directos.route("/", methods=["GET"])
@login_required
@require_modulo('gastos_directos')
def form_gastos_directos():
    """Vista principal del módulo de gastos directos"""
    try:
        # Usar datos cacheados para mejorar performance
        proyectos = get_cached_proyectos_with_id()
        items = get_cached_items_with_id()
        
        meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        
        current_app.logger.info(f"Usuario {current_user.nombre} accedió al módulo de gastos directos")
        
        return render_template(
            "gastos_directos.html",
            proyectos=proyectos,
            items=items,
            meses=meses,
            hoy=date.today()
        )
    except Exception as e:
        current_app.logger.error(f"Error en form_gastos_directos: {e}")
        flash("Error al cargar el módulo de gastos directos", "danger")
        return redirect(url_for('auth.home'))

@bp_gastos_directos.route("/guardar", methods=["POST"])
@login_required
@require_modulo('gastos_directos')
def guardar_gastos_directos():
    """Guardar múltiples gastos directos"""
    try:
        supabase = current_app.config["SUPABASE"]
        data = request.get_json()
        
        if not data:
            return jsonify(success=False, message="No se recibieron datos"), 400
        
        gastos = data.get("gastos", [])
        proyecto_id = data.get("proyecto_id")
        usuario_id = current_user.id
        
        # Validaciones
        if not proyecto_id:
            return jsonify(success=False, message="Debe seleccionar un proyecto")
        
        if not gastos:
            return jsonify(success=False, message="Debe agregar al menos un gasto")
        
        # Validar que el proyecto existe
        proyecto_check = supabase.table("proyectos").select("id").eq("id", proyecto_id).limit(1).execute()
        if not proyecto_check.data:
            return jsonify(success=False, message="El proyecto seleccionado no existe")
        
        errores = []
        gastos_guardados = 0
        
        for i, gasto in enumerate(gastos):
            try:
                # Validar campos requeridos
                if not all([gasto.get("item_id"), gasto.get("mes"), gasto.get("monto")]):
                    errores.append(f"Gasto {i+1}: Faltan campos obligatorios")
                    continue
                
                # Validar monto
                try:
                    monto = int(gasto["monto"])
                    if monto <= 0:
                        errores.append(f"Gasto {i+1}: El monto debe ser mayor a 0")
                        continue
                except (ValueError, TypeError):
                    errores.append(f"Gasto {i+1}: Monto inválido")
                    continue
                
                # Validar que el item existe
                item_check = supabase.table("item").select("id").eq("id", gasto["item_id"]).limit(1).execute()
                if not item_check.data:
                    errores.append(f"Gasto {i+1}: El ítem seleccionado no existe")
                    continue
                
                # Insertar gasto
                resultado = supabase.table("gastos_directos").insert({
                    "fecha": date.today().isoformat(),
                    "proyecto_id": int(proyecto_id),
                    "item_id": int(gasto["item_id"]),
                    "descripcion": gasto.get("descripcion", "").strip()[:255],  # Limitar a 255 caracteres
                    "mes": gasto["mes"],
                    "monto": monto,
                    "usuario_id": usuario_id
                }).execute()
                
                if resultado.data:
                    gastos_guardados += 1
                else:
                    errores.append(f"Gasto {i+1}: Error al guardar en la base de datos")
                    
            except Exception as e:
                current_app.logger.error(f"Error guardando gasto {i+1}: {e}")
                errores.append(f"Gasto {i+1}: {str(e)}")
        
        # Registrar actividad
        current_app.logger.info(f"Usuario {current_user.nombre} guardó {gastos_guardados} gastos directos para proyecto {proyecto_id}")
        
        if errores and gastos_guardados == 0:
            return jsonify(success=False, message="No se pudo guardar ningún gasto: " + "; ".join(errores))
        elif errores:
            return jsonify(success=True, message=f"Se guardaron {gastos_guardados} gastos. Errores: " + "; ".join(errores))
        else:
            return jsonify(success=True, message=f"Se guardaron {gastos_guardados} gastos correctamente.")
            
    except Exception as e:
        current_app.logger.error(f"Error en guardar_gastos_directos: {e}")
        return jsonify(success=False, message="Error interno del servidor"), 500

@bp_gastos_directos.route("/api/gastos/<int:proyecto_id>", methods=["GET"])
@login_required
@require_modulo('gastos_directos')
def api_gastos_proyecto(proyecto_id):
    """API para obtener gastos de un proyecto específico"""
    try:
        supabase = current_app.config["SUPABASE"]
        
        # Obtener gastos del proyecto
        gastos = supabase.table("gastos_directos") \
            .select("*, item:item_id(tipo)") \
            .eq("proyecto_id", proyecto_id) \
            .order("fecha", desc=True) \
            .execute().data or []
        
        return jsonify(success=True, gastos=gastos)
        
    except Exception as e:
        current_app.logger.error(f"Error en api_gastos_proyecto: {e}")
        return jsonify(success=False, message="Error al obtener gastos"), 500

@bp_gastos_directos.route("/eliminar/<int:gasto_id>", methods=["DELETE"])
@login_required
@require_modulo('gastos_directos')
def eliminar_gasto(gasto_id):
    """Eliminar un gasto directo específico"""
    try:
        supabase = current_app.config["SUPABASE"]
        
        # Verificar que el gasto existe y pertenece al usuario (opcional: agregar validación de permisos)
        gasto_check = supabase.table("gastos_directos") \
            .select("id, usuario_id") \
            .eq("id", gasto_id) \
            .limit(1) \
            .execute()
        
        if not gasto_check.data:
            return jsonify(success=False, message="El gasto no existe"), 404
        
        # Eliminar gasto
        resultado = supabase.table("gastos_directos") \
            .delete() \
            .eq("id", gasto_id) \
            .execute()
        
        if resultado.data:
            current_app.logger.info(f"Usuario {current_user.nombre} eliminó el gasto directo {gasto_id}")
            return jsonify(success=True, message="Gasto eliminado correctamente")
        else:
            return jsonify(success=False, message="Error al eliminar el gasto")
            
    except Exception as e:
        current_app.logger.error(f"Error en eliminar_gasto: {e}")
        return jsonify(success=False, message="Error interno del servidor"), 500