import json
from flask import request, current_app
from flask_login import current_user
from datetime import datetime

def registrar_log_actividad(accion, tabla_afectada=None, registro_id=None, descripcion=None, datos_antes=None, datos_despues=None):
    """
    Registra una acción de usuario en la tabla logs_actividad usando Supabase.
    """
    supabase = current_app.config["SUPABASE"]
    usuario_id = getattr(current_user, 'id', None)
    ip_origen = request.remote_addr
    user_agent = request.user_agent.string if request.user_agent else None

    # Convertir a JSON si es necesario
    if datos_antes is not None and not isinstance(datos_antes, str):
        datos_antes = json.dumps(datos_antes, default=str)
    if datos_despues is not None and not isinstance(datos_despues, str):
        datos_despues = json.dumps(datos_despues, default=str)

    log_data = {
        "usuario_id": usuario_id,
        "accion": accion,
        "tabla_afectada": tabla_afectada,
        "registro_id": registro_id,
        "descripcion": descripcion,
        "datos_antes": datos_antes,
        "datos_despues": datos_despues,
        "ip_origen": ip_origen,
        "user_agent": user_agent,
        "fecha_hora": datetime.now().isoformat()
    }
    # Eliminar claves None para evitar problemas con Supabase
    log_data = {k: v for k, v in log_data.items() if v is not None}
    try:
        supabase.table("logs_actividad").insert(log_data).execute()
    except Exception as e:
        current_app.logger.error(f"Error al registrar log de actividad: {e}")
