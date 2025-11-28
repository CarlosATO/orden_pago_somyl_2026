"""
Módulo de proyectos adaptado para trabajar con frontend React
Mantiene compatibilidad con estructura existente
"""

from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required

bp = Blueprint("proyectos", __name__)


def _clean_upper(val):
    """Normaliza un valor a string, strip y upper de forma segura."""
    if val is None:
        return ''
    try:
        return str(val).strip().upper()
    except Exception:
        return ''


@bp.route("/", methods=["GET"])
@token_required
def get_proyectos(current_user):
    """
    Devuelve una lista de proyectos activos en formato JSON.
    Endpoint principal para obtener proyectos
    """
    try:
        supabase = current_app.config['SUPABASE']

        # Obtenemos solo proyectos activos ordenados por nombre
        response = supabase.table("proyectos").select("*").eq("activo", True).order("proyecto").execute()

        proyectos = response.data or []

        return jsonify({
            "success": True,
            "data": proyectos  # Cambiado de "proyectos" a "data" para consistencia
        })

    except Exception as e:
        current_app.logger.exception(f"Error al obtener proyectos: {e}")
        return jsonify({"success": False, "message": "Error al obtener los proyectos"}), 500


@bp.route("/api/activos", methods=["GET"])
@token_required
def api_get_proyectos_activos(current_user):
    """
    Devuelve una lista de proyectos activos en formato JSON.
    """
    try:
        supabase = current_app.config['SUPABASE']

        # Obtenemos solo proyectos activos ordenados por nombre
        response = supabase.table("proyectos").select("*").eq("activo", True).order("proyecto").execute()

        proyectos = response.data or []

        return jsonify({
            "success": True,
            "data": proyectos
        })

    except Exception as e:
        current_app.logger.exception(f"Error en API de proyectos: {e}")
        return jsonify({"success": False, "message": "Error al obtener los proyectos"}), 500


@bp.route("/new", methods=["POST"])
@token_required
def new_proyecto(current_user):
    """Crea un nuevo proyecto"""
    try:
        data = request.get_json() or {}

        # Validar y limpiar datos de entrada (manejar tipos no-string)
        proyecto_val = _clean_upper(data.get("proyecto"))
        venta_val = _clean_upper(data.get("venta"))
        observacion_val = _clean_upper(data.get("observacion"))

        # Validaciones básicas
        if not proyecto_val:
            return jsonify({"success": False, "message": "El nombre del proyecto es obligatorio"}), 400
        
        if len(proyecto_val) < 3:
            return jsonify({"success": False, "message": "El nombre del proyecto debe tener al menos 3 caracteres"}), 400

        supabase = current_app.config['SUPABASE']

        # Verificar duplicado
        dup = supabase.table("proyectos").select("id").eq("proyecto", proyecto_val).execute().data
        
        if dup:
            return jsonify({"success": False, "message": f"El proyecto '{proyecto_val}' ya existe"}), 400

        # Preparar payload
        def to_null(val):
            if not val or str(val).strip().upper() == "NONE":
                return None
            return val

        payload = {
            "proyecto": proyecto_val,
            "venta": to_null(venta_val),
            "observacion": to_null(observacion_val),
            "activo": True
        }

        # Insertar proyecto
        result = supabase.table("proyectos").insert(payload).execute()
        
        if result.data:
            current_app.logger.info(f"Proyecto creado: {proyecto_val}")
            return jsonify({
                "success": True,
                "data": result.data[0] if isinstance(result.data, list) else result.data,
                "message": f"Proyecto '{proyecto_val}' creado exitosamente"
            })
        else:
            return jsonify({"success": False, "message": "Error al crear el proyecto"}), 500

    except Exception as e:
        current_app.logger.exception(f"Error al crear proyecto: {e}")
        return jsonify({"success": False, "message": "Error interno al crear el proyecto"}), 500


@bp.route("/edit/<int:id>", methods=["GET", "POST"])
@token_required
def edit_proyecto(current_user, id):
    """Edita un proyecto existente"""
    supabase = current_app.config['SUPABASE']
    
    try:
        # Obtener proyecto actual
        proyecto = supabase.table("proyectos").select("*").eq("id", id).execute().data
        if not proyecto:
            return jsonify({"success": False, "message": "Proyecto no encontrado"}), 404
        
        proyecto = proyecto[0]

        if request.method == 'GET':
            return jsonify({"success": True, "data": proyecto})

        # POST - actualizar
        data = request.get_json() or {}

        # Validar y limpiar datos (manejar tipos no-string)
        proyecto_val = _clean_upper(data.get("proyecto"))
        venta_val = _clean_upper(data.get("venta"))
        observacion_val = _clean_upper(data.get("observacion"))

        if not proyecto_val:
            return jsonify({"success": False, "message": "El nombre del proyecto es obligatorio"}), 400
        
        if len(proyecto_val) < 3:
            return jsonify({"success": False, "message": "El nombre debe tener al menos 3 caracteres"}), 400

        # Verificar duplicado (excluyendo el actual)
        if proyecto_val != proyecto["proyecto"]:
            dup = supabase.table("proyectos").select("id").eq("proyecto", proyecto_val).execute().data
            if dup and any(d.get('id') != id for d in dup):
                return jsonify({"success": False, "message": f"Ya existe otro proyecto con el nombre '{proyecto_val}'"}), 400

        # Preparar payload
        def to_null(val):
            if not val or str(val).strip().upper() == "NONE":
                return None
            return val

        payload = {
            "proyecto": proyecto_val,
            "venta": to_null(venta_val),
            "observacion": to_null(observacion_val)
        }

        # Actualizar proyecto
        result = supabase.table("proyectos").update(payload).eq("id", id).execute()
        
        if result.data:
            current_app.logger.info(f"Proyecto actualizado: {proyecto_val} (ID: {id})")
            return jsonify({
                "success": True,
                "data": result.data[0] if isinstance(result.data, list) else result.data,
                "message": f"Proyecto '{proyecto_val}' actualizado exitosamente"
            })
        else:
            return jsonify({"success": False, "message": "Error al actualizar el proyecto"}), 500

    except Exception as e:
        current_app.logger.exception(f"Error al editar proyecto ID {id}: {e}")
        return jsonify({"success": False, "message": "Error interno al procesar el proyecto"}), 500


@bp.route("/api/search", methods=["GET"])
@token_required
def api_search(current_user):
    """API para búsqueda de proyectos (para select/autocomplete)"""
    try:
        term = request.args.get("term", "").strip()
        
        if not term:
            return jsonify({"results": []})
        
        supabase = current_app.config['SUPABASE']
        proyectos = (
            supabase.table("proyectos")
            .select("id, proyecto")
            .ilike("proyecto", f"%{term}%")
            .limit(20)
            .execute()
            .data or []
        )
        
        results = [{"id": p["id"], "text": p["proyecto"]} for p in proyectos]
        return jsonify({"results": results})
        
    except Exception as e:
        current_app.logger.exception(f"Error en búsqueda de proyectos: {e}")
        return jsonify({"results": []})


@bp.route("/api/stats", methods=["GET"])
@token_required
def api_stats(current_user):
    """API para estadísticas de proyectos"""
    try:
        supabase = current_app.config['SUPABASE']
        proyectos = supabase.table("proyectos").select("venta").execute().data or []
        
        total = len(proyectos)
        con_venta = len([p for p in proyectos if p.get("venta")])
        sin_venta = total - con_venta
        
        return jsonify({
            "total": total,
            "con_venta": con_venta,
            "sin_venta": sin_venta
        })
        
    except Exception as e:
        current_app.logger.exception(f"Error al obtener estadísticas de proyectos: {e}")
        return jsonify({"total": 0, "con_venta": 0, "sin_venta": 0})
