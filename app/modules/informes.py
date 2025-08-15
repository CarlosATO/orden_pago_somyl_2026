# IMPORTS AL INICIO
from flask import Blueprint, render_template, current_app, jsonify, request
from flask_login import login_required
import logging
from typing import Dict, List, Optional, Any, Tuple
from functools import wraps

# Configuración del blueprint
bp = Blueprint("informes", __name__, template_folder="../templates/informes")

# Configurar logging una sola vez
logger = logging.getLogger(__name__)

# CONSTANTES
ELIMINA_OC_FLAG = "1"
DEFAULT_PAGE_SIZE = 1000
ART_CORR_DEFAULT = "0"

class DatabaseError(Exception):
    """Excepción personalizada para errores de base de datos"""
    pass

class ValidationError(Exception):
    """Excepción personalizada para errores de validación"""
    pass

def handle_database_errors(f):
    """Decorador para manejar errores de base de datos"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error en {f.__name__}: {str(e)}")
            return jsonify({"error": "Error interno del servidor"}), 500
    return decorated_function

def safe_str(value: Any, default: str = "") -> str:
    """Convierte un valor a string de forma segura"""
    return str(value) if value is not None else default

def safe_float(value: Any, default: float = 0.0) -> float:
    """Convierte un valor a float de forma segura"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"No se pudo convertir {value} a float, usando {default}")
        return default

def safe_int(value: Any, default: int = 0) -> int:
    """Convierte un valor a int de forma segura"""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"No se pudo convertir {value} a int, usando {default}")
        return default

def normalize_art_corr(art_corr: Any) -> str:
    """Normaliza el campo art_corr de forma consistente"""
    if art_corr is None:
        return ART_CORR_DEFAULT
    
    normalized = safe_str(art_corr).strip().lstrip('0')
    return normalized if normalized else ART_CORR_DEFAULT

def validate_oc(oc: str) -> bool:
    """Valida que OC sea un valor válido"""
    if not oc or not oc.strip():
        return False
    try:
        int(oc)
        return True
    except ValueError:
        return False

def get_supabase():
    """Obtiene la instancia de Supabase de forma segura"""
    supabase = current_app.config.get("SUPABASE")
    if not supabase:
        raise DatabaseError("Configuración de Supabase no encontrada")
    return supabase

def get_proveedores_map(supabase) -> Dict[str, str]:
    """Función auxiliar para obtener el mapa de proveedores"""
    try:
        response = supabase.table("proveedores").select("id, nombre").execute()
        proveedores = response.data or []
        return {str(p["id"]): p["nombre"] for p in proveedores if p.get("id") and p.get("nombre")}
    except Exception as e:
        logger.error(f"Error obteniendo proveedores: {e}")
        return {}

def check_ingresos_exist(supabase, oc: str) -> bool:
    """Verifica si existen ingresos asociados a una OC"""
    try:
        response = supabase.table("ingresos").select("id").eq("orden_compra", oc).limit(1).execute()
        return len(response.data or []) > 0
    except Exception as e:
        logger.error(f"Error verificando ingresos para OC {oc}: {e}")
        raise DatabaseError(f"Error verificando ingresos: {e}")

def get_oc_lines(supabase, oc: str) -> List[Dict[str, Any]]:
    """Obtiene las líneas de una orden de compra"""
    columnas = [
        "orden_compra", "proveedor", "fecha", "codigo", "descripcion", 
        "cantidad", "precio_unitario", "total", "tipo", "art_corr"
    ]
    
    try:
        response = supabase.table("orden_de_compra").select(*columnas).eq("orden_compra", oc).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Error obteniendo líneas de OC {oc}: {e}")
        raise DatabaseError(f"Error obteniendo datos de OC: {e}")

def get_all_ingresos(supabase) -> List[Dict[str, Any]]:
    """Obtiene todos los ingresos con paginación optimizada"""
    all_ingresos = []
    start = 0
    
    while True:
        try:
            response = supabase.table("ingresos").select("orden_compra, art_corr").range(
                start, start + DEFAULT_PAGE_SIZE - 1
            ).execute()
            rows = response.data or []
            
            if not rows:
                break
                
            all_ingresos.extend(rows)
            
            if len(rows) < DEFAULT_PAGE_SIZE:
                break
                
            start += DEFAULT_PAGE_SIZE
            
        except Exception as e:
            logger.error(f"Error obteniendo ingresos en página {start}: {e}")
            break
    
    return all_ingresos

def create_ingresos_set(ingresos: List[Dict[str, Any]]) -> set:
    """Crea un conjunto de claves (oc, art_corr) de ingresos"""
    ingresos_set = set()
    for ing in ingresos:
        orden_compra = safe_str(ing.get("orden_compra"))
        art_corr = normalize_art_corr(ing.get("art_corr"))
        if orden_compra:  # Solo agregar si orden_compra no está vacía
            ingresos_set.add((orden_compra, art_corr))
    return ingresos_set

# ENDPOINTS

@bp.route("/api/oc_sacar_informe/<oc>", methods=["POST"])
@login_required
@handle_database_errors
def api_oc_sacar_informe(oc: str):
    if not validate_oc(oc):
        return jsonify({"error": "OC inválida"}), 400
    
    supabase = get_supabase()
    
    try:
        updated = supabase.table("orden_de_compra").update(
            {"elimina_oc": ELIMINA_OC_FLAG}
        ).eq("orden_compra", oc).execute()
        
        count = getattr(updated, 'count', 0)
        logger.info(f"OC {oc} marcada para eliminar. Registros actualizados: {count}")
        
        return jsonify({"success": True, "updated": count})
        
    except Exception as e:
        logger.error(f"Error marcando OC {oc} para eliminar: {e}")
        raise DatabaseError(f"Error actualizando OC: {e}")

@bp.route("/api/oc_detalle/<oc>", methods=["GET"])
@login_required
@handle_database_errors
def api_oc_detalle(oc: str):
    if not validate_oc(oc):
        return jsonify({"error": "OC inválida"}), 400
    
    supabase = get_supabase()
    
    # Obtener líneas de la OC
    oc_lines = get_oc_lines(supabase, oc)
    if not oc_lines:
        return jsonify({"error": "OC no encontrada"}), 404
    
    # Obtener información del proveedor
    proveedor_id = safe_str(oc_lines[0].get("proveedor"))
    proveedor_map = get_proveedores_map(supabase)
    proveedor = proveedor_map.get(proveedor_id, proveedor_id)
    fecha = oc_lines[0].get("fecha")
    
    # Procesar líneas
    lineas = []
    for ln in oc_lines:
        lineas.append({
            "codigo": ln.get("codigo", "-"),
            "descripcion": ln.get("descripcion", "-"),
            "cantidad": safe_int(ln.get("cantidad")),
            "precio_unitario": safe_float(ln.get("precio_unitario")),
            "total": safe_float(ln.get("total")),
            "tipo": ln.get("tipo", "-"),
            "art_corr": normalize_art_corr(ln.get("art_corr"))
        })
    
    # Verificar si puede eliminarse
    puede_eliminar = not check_ingresos_exist(supabase, oc)
    
    return jsonify({
        "orden_compra": oc,
        "proveedor": proveedor,
        "fecha": fecha,
        "lineas": lineas,
        "puede_eliminar": puede_eliminar
    })

@bp.route("/api/oc_eliminar/<oc>", methods=["POST"])
@login_required
@handle_database_errors
def api_oc_eliminar(oc: str):
    if not validate_oc(oc):
        return jsonify({"error": "OC inválida"}), 400
    
    supabase = get_supabase()
    
    # Validar que no existan ingresos asociados
    if check_ingresos_exist(supabase, oc):
        return jsonify({
            "error": "No se puede eliminar la orden porque tiene ingresos asociados."
        }), 400
    
    try:
        deleted = supabase.table("orden_de_compra").delete().eq("orden_compra", oc).execute()
        count = getattr(deleted, 'count', 0)
        
        logger.info(f"OC {oc} eliminada. Registros eliminados: {count}")
        
        return jsonify({"success": True, "deleted": count})
        
    except Exception as e:
        logger.error(f"Error eliminando OC {oc}: {e}")
        raise DatabaseError(f"Error eliminando OC: {e}")

@bp.route("/oc_no_recepcionadas", methods=["GET"], endpoint="oc_no_recepcionadas")
@login_required
@handle_database_errors
def oc_no_recepcionadas():
    supabase = get_supabase()
    
    try:
        # Obtener líneas de órdenes de compra
        response = supabase.table("orden_de_compra").select(
            "orden_compra, proveedor, fecha, total, art_corr, elimina_oc"
        ).order("orden_compra", desc=True).execute()
        oc_lines = response.data or []

        # Filtrar OCs que no estén marcadas como eliminadas
        oc_lines = [ln for ln in oc_lines if safe_str(ln.get("elimina_oc")) != ELIMINA_OC_FLAG]
        
        # Obtener mapeo de proveedores
        proveedor_map = get_proveedores_map(supabase)
        
        # Obtener todos los ingresos
        ingresos = get_all_ingresos(supabase)
        ingresos_set = create_ingresos_set(ingresos)
        
        # Procesar OCs pendientes
        oc_pendientes = {}
        for ln in oc_lines:
            oc = safe_str(ln.get("orden_compra"))
            if not oc:
                continue
                
            proveedor_id = safe_str(ln.get("proveedor"))
            proveedor = proveedor_map.get(proveedor_id, proveedor_id)
            fecha = ln.get("fecha")
            monto_total = safe_float(ln.get("total"))
            
            art_corr = normalize_art_corr(ln.get("art_corr"))
            clave = (oc, art_corr)
            
            # Si no está en ingresos, es pendiente
            if clave not in ingresos_set:
                if oc not in oc_pendientes:
                    oc_pendientes[oc] = {
                        "orden_compra": oc,
                        "proveedor": proveedor,
                        "fecha": fecha,
                        "monto_total": 0.0,
                        "estado": "Pendiente"
                    }
                oc_pendientes[oc]["monto_total"] += monto_total
        
        # Preparar respuesta
        pendientes = list(oc_pendientes.values())
        total_oc = len(pendientes)
        total_monto = sum(p["monto_total"] for p in pendientes)
        
        logger.info(f"Procesadas {len(oc_lines)} líneas de OC, {total_oc} OCs pendientes")
        
        return render_template(
            "informes/oc_no_recepcionadas.html",
            pendientes=pendientes,
            total_oc=total_oc,
            total_monto=total_monto
        )
        
    except Exception as e:
        logger.error(f"Error generando informe de OCs no recepcionadas: {e}")
        raise DatabaseError(f"Error generando informe: {e}")