# app/modules/proyectos.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, request as flask_request
from app.modules.usuarios import require_modulo
from flask_login import current_user
from utils.logger import registrar_log_actividad
import logging

bp = Blueprint("proyectos", __name__, template_folder="../templates/proyectos")

@bp.route("/", methods=["GET"])
@require_modulo('proyectos')
def list_proyectos():
    """Lista todos los proyectos registrados"""
    try:
        proyectos = (
            current_app.config['SUPABASE']
            .table("proyectos")
            .select("*")
            .order("proyecto")
            .execute()
            .data or []
        )
        
        # Log para debug
        current_app.logger.info(f"Proyectos cargados: {len(proyectos)}")
        
        return render_template("proyectos/form.html", proyectos=proyectos)
        
    except Exception as e:
        current_app.logger.error(f"Error al cargar proyectos: {e}")
        flash("Error al cargar los proyectos. Intente nuevamente.", "danger")
        return render_template("proyectos/form.html", proyectos=[])

@bp.route("/new", methods=["POST"])
@require_modulo('proyectos')
def new_proyecto():
    """Crea un nuevo proyecto"""
    try:
        # Validar y limpiar datos de entrada
        proyecto_val = request.form.get("proyecto", "").strip().upper()
        venta_val = request.form.get("venta", "").strip().upper()
        observacion_val = request.form.get("observacion", "").strip().upper()

        # Validaciones básicas
        if not proyecto_val:
            flash("El nombre del proyecto es obligatorio.", "danger")
            return redirect(url_for("proyectos.list_proyectos"))
        
        if len(proyecto_val) < 3:
            flash("El nombre del proyecto debe tener al menos 3 caracteres.", "danger")
            return redirect(url_for("proyectos.list_proyectos"))

        # Verificar duplicado en columna 'proyecto'
        dup = (
            current_app.config['SUPABASE']
            .table("proyectos")
            .select("id")
            .eq("proyecto", proyecto_val)
            .execute()
            .data
        )
        
        if dup:
            flash(f"El proyecto '{proyecto_val}' ya existe.", "danger")
            return redirect(url_for("proyectos.list_proyectos"))

        # Crear nuevo proyecto
        payload = {
            "proyecto": proyecto_val,
            "venta": venta_val if venta_val else None,
            "observacion": observacion_val if observacion_val else None
        }
        
        result = current_app.config['SUPABASE'].table("proyectos").insert(payload).execute()
        if result.data:
            proyecto_id = result.data[0]["id"] if isinstance(result.data, list) and result.data else None
            current_app.logger.info(f"Proyecto creado: {proyecto_val}")
            # Log de actividad
            registrar_log_actividad(
                accion="crear",
                tabla_afectada="proyectos",
                registro_id=proyecto_id,
                descripcion=f"Proyecto '{proyecto_val}' creado.",
                datos_antes=None,
                datos_despues=payload
            )
            flash(f"Proyecto '{proyecto_val}' creado exitosamente.", "success")
            # Invalidar cache de proyectos para búsquedas (Select2)
            from app.utils.cache import invalidate_select2_cache
            invalidate_select2_cache("proyectos")
        else:
            current_app.logger.error(f"Error al crear proyecto: {result}")
            flash("Error al crear el proyecto. Intente nuevamente.", "danger")
        return redirect(url_for("proyectos.list_proyectos"))
        
    except Exception as e:
        current_app.logger.error(f"Error al crear proyecto: {e}")
        flash("Error interno al crear el proyecto. Contacte al administrador.", "danger")
        return redirect(url_for("proyectos.list_proyectos"))

@bp.route("/edit/<int:id>", methods=["GET", "POST"])
@require_modulo('proyectos')
def edit_proyecto(id):
    """Edita un proyecto existente"""
    try:
        # Obtener proyecto actual
        res = (
            current_app.config['SUPABASE']
            .table("proyectos")
            .select("*")
            .eq("id", id)
            .execute()
        )
        
        proyecto = (res.data or [None])[0]
        if not proyecto:
            flash("Proyecto no encontrado.", "danger")
            return redirect(url_for("proyectos.list_proyectos"))

        if request.method == "POST":
            # Validar y limpiar datos de entrada
            nuevos = {
                "proyecto": request.form.get("proyecto", "").strip().upper(),
                "venta": request.form.get("venta", "").strip().upper(),
                "observacion": request.form.get("observacion", "").strip().upper()
            }

            # Validaciones básicas
            if not nuevos["proyecto"]:
                flash("El nombre del proyecto es obligatorio.", "danger")
                proyectos = (
                    current_app.config['SUPABASE']
                    .table("proyectos")
                    .select("*")
                    .order("proyecto")
                    .execute()
                    .data or []
                )
                return render_template("proyectos/form.html", proyectos=proyectos, proyecto=proyecto)
            
            if len(nuevos["proyecto"]) < 3:
                flash("El nombre del proyecto debe tener al menos 3 caracteres.", "danger")
                proyectos = (
                    current_app.config['SUPABASE']
                    .table("proyectos")
                    .select("*")
                    .order("proyecto")
                    .execute()
                    .data or []
                )
                return render_template("proyectos/form.html", proyectos=proyectos, proyecto=proyecto)

            # Verificar duplicado solo si cambió el nombre
            if nuevos["proyecto"] != proyecto["proyecto"]:
                dup = (
                    current_app.config['SUPABASE']
                    .table("proyectos")
                    .select("id")
                    .eq("proyecto", nuevos["proyecto"])
                    .execute()
                    .data
                )
                if dup:
                    flash(f"El proyecto '{nuevos['proyecto']}' ya existe.", "danger")
                    proyectos = (
                        current_app.config['SUPABASE']
                        .table("proyectos")
                        .select("*")
                        .order("proyecto")
                        .execute()
                        .data or []
                    )
                    return render_template("proyectos/form.html", proyectos=proyectos, proyecto=proyecto)

            # Preparar payload con valores nulos apropiados
            payload = {
                "proyecto": nuevos["proyecto"],
                "venta": nuevos["venta"] if nuevos["venta"] else None,
                "observacion": nuevos["observacion"] if nuevos["observacion"] else None
            }

            # Actualizar proyecto
            result = (
                current_app.config['SUPABASE']
                .table("proyectos")
                .update(payload)
                .eq("id", id)
                .execute()
            )
            if result.data:
                current_app.logger.info(f"Proyecto actualizado: {nuevos['proyecto']} (ID: {id})")
                # Log de actividad
                registrar_log_actividad(
                    accion="actualizar",
                    tabla_afectada="proyectos",
                    registro_id=id,
                    descripcion=f"Proyecto '{nuevos['proyecto']}' actualizado.",
                    datos_antes=proyecto,
                    datos_despues=payload
                )
                flash(f"Proyecto '{nuevos['proyecto']}' actualizado exitosamente.", "success")
            else:
                current_app.logger.error(f"Error al actualizar proyecto ID {id}: {result}")
                flash("Error al actualizar el proyecto. Intente nuevamente.", "danger")
            return redirect(url_for("proyectos.list_proyectos"))

        # GET: mostrar formulario de edición
        proyectos = (
            current_app.config['SUPABASE']
            .table("proyectos")
            .select("*")
            .order("proyecto")
            .execute()
            .data or []
        )
        
        return render_template("proyectos/form.html", proyectos=proyectos, proyecto=proyecto)
        
    except Exception as e:
        current_app.logger.error(f"Error al editar proyecto ID {id}: {e}")
        flash("Error interno al procesar el proyecto. Contacte al administrador.", "danger")
        return redirect(url_for("proyectos.list_proyectos"))

@bp.route("/api/search", methods=["GET"])
@require_modulo('proyectos')
def api_search():
    """API para búsqueda de proyectos"""
    try:
        term = request.args.get("term", "").strip()
        
        if not term:
            return jsonify({"results": []})
        
        proyectos = (
            current_app.config['SUPABASE']
            .table("proyectos")
            .select("id, proyecto")
            .ilike("proyecto", f"%{term}%")
            .limit(20)
            .execute()
            .data or []
        )
        
        results = [{"id": p["id"], "text": p["proyecto"]} for p in proyectos]
        return jsonify({"results": results})
        
    except Exception as e:
        current_app.logger.error(f"Error en búsqueda de proyectos: {e}")
        return jsonify({"results": []})

@bp.route("/api/stats", methods=["GET"])
@require_modulo('proyectos')
def api_stats():
    """API para estadísticas de proyectos"""
    try:
        proyectos = (
            current_app.config['SUPABASE']
            .table("proyectos")
            .select("venta")
            .execute()
            .data or []
        )
        
        total = len(proyectos)
        con_venta = len([p for p in proyectos if p.get("venta")])
        sin_venta = total - con_venta
        
        return jsonify({
            "total": total,
            "con_venta": con_venta,
            "sin_venta": sin_venta
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener estadísticas de proyectos: {e}")
        return jsonify({"total": 0, "con_venta": 0, "sin_venta": 0})