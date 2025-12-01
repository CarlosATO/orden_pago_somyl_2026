from flask import Blueprint, request, current_app, jsonify
from collections import deque
import time
import logging
import requests
import google.generativeai as genai
import os
import json

# IMPORTAMOS TUS ESPECIALISTAS (INTACTOS)
from .bot_tools import chat_proveedores, operaciones, chat_proyectos, chat_pagos, chat_ordenes, chat_materiales
from .bot_tools.base import extract_order_number, safe_generate

bp = Blueprint("chatbot", __name__)

# Trace store en memoria
INTERACTIONS = deque(maxlen=200)

# --- CONFIGURACIÓN ---
# Nuevas variables para Meta
VERIFY_TOKEN = os.environ.get("META_VERIFY_TOKEN")      # Tu contraseña inventada para el webhook
WHATSAPP_TOKEN = os.environ.get("META_WHATSAPP_TOKEN")  # Token (comienza con EAA...)
PHONE_NUMBER_ID = os.environ.get("META_PHONE_ID")       # ID del teléfono (no el número, el ID)

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
model = None

logger = logging.getLogger(__name__)

# Configuración Gemini
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        logger.info("✅ Cerebro Gemini conectado")
    except Exception as e:
        logger.error(f"❌ Error Gemini: {e}")
else:
    logger.warning("⚠️ FALTA LA CLAVE GEMINI")


@bp.route('/health', methods=['GET'])
def chatbot_health():
    """Estado de salud del bot."""
    return {
        'status': 'ok',
        'provider': 'meta_cloud_api',
        'llm': bool(model)
    }

@bp.route('/trace', methods=['GET'])
def chatbot_trace():
    """Historial de debug."""
    return jsonify({'success': True, 'items': list(INTERACTIONS)[:50]})


def enviar_mensaje_meta(telefono, texto):
    """Envía la respuesta a la API de WhatsApp Cloud."""
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        logger.error("❌ Faltan credenciales de Meta (Token o Phone ID)")
        return

    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto}
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje a Meta: {e}")
        if 'response' in locals():
            logger.error(f"Detalle Meta: {response.text}")


def clasificar_intencion(texto):
    """Misma lógica de clasificación que ya tenías."""
    # 1. Heurísticas rápidas
    oc_num = extract_order_number(texto)
    if oc_num: return f"ESTADO_OC|{oc_num}"

    lower = texto.lower()
    if any(k in lower for k in ['proveedor', 'rut', 'fono', 'correo']): return 'PROVEEDORES'
    if any(k in lower for k in ['proyecto', 'obra']): return 'PROYECTOS'
    if any(k in lower for k in ['deuda', 'pago', 'saldo']): return 'PAGOS'
    if any(k in lower for k in ['orden', 'oc ', 'compra']): return 'ORDENES'
    if any(k in lower for k in ['material', 'stock']): return 'MATERIALES'

    # 2. Fallback LLM
    if not model: return 'CHARLA'

    prompt = f"""
    Analiza: "{texto}"
    Clasifica en: PROVEEDORES, PROYECTOS, ESTADO_OC|Numero, PAGOS, o CHARLA.
    Solo responde la categoría.
    """
    try:
        respuesta = safe_generate(model, prompt, default='CHARLA')
        return respuesta.replace('"', '').strip() if respuesta else 'CHARLA'
    except:
        return 'CHARLA'


# ==========================================
# RUTAS DEL WEBHOOK (VERIFICACIÓN Y MENSAJES)
# ==========================================

@bp.route("/webhook", methods=['GET'])
def verify_webhook():
    """Ruta para validar el webhook con Meta."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            logger.info("✅ Webhook verificado correctamente.")
            return challenge, 200
        else:
            logger.warning("❌ Fallo verificación de webhook (token incorrecto).")
            return "Forbidden", 403
    return "Webhook configurado (esperando GET de verificación)", 200


@bp.route("/webhook", methods=['POST'])
def whatsapp_reply():
    """Recibe mensajes, procesa y responde asíncronamente (HTTP request a Meta)."""
    body = request.get_json()
    
    # Validar que sea un evento de mensaje
    try:
        if not body or body.get("object") != "whatsapp_business_account":
            return jsonify({"status": "ignored"}), 200

        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # Solo nos interesan los mensajes, no los estados (sent, delivered, etc)
                if "messages" in value:
                    for message in value["messages"]:
                        # Solo procesamos texto por ahora
                        if message["type"] == "text":
                            procesar_mensaje_entrante(message)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.exception(f"Error procesando webhook: {e}")
        return jsonify({"status": "error"}), 500


def procesar_mensaje_entrante(message_data):
    """Lógica principal de respuesta separada de la ruta."""
    db = current_app.config.get('SUPABASE')
    
    telefono = message_data['from']  # El ID del usuario (número)
    texto_usuario = message_data['text']['body']
    
    logger.info(f"📩 Mensaje de {telefono}: {texto_usuario}")
    
    respuesta = None
    intencion_raw = "DESCONOCIDA"

    try:
        # 1. Clasificar
        intencion_raw = clasificar_intencion(texto_usuario)
        logger.info(f"🧠 Intención: {intencion_raw}")

        # 2. Enrutar
        if "PROVEEDORES" in intencion_raw:
            respuesta = chat_proveedores.procesar_consulta(texto_usuario, db, model)
        elif "PROYECTOS" in intencion_raw:
            respuesta = chat_proyectos.procesar_consulta(texto_usuario, db, model)
        elif "PAGOS" in intencion_raw:
            respuesta = chat_pagos.procesar_consulta(texto_usuario, db, model)
        elif "ORDENES" in intencion_raw:
            respuesta = chat_ordenes.procesar_consulta(texto_usuario, db, model)
        elif "MATERIALES" in intencion_raw:
            respuesta = chat_materiales.procesar_consulta(texto_usuario, db, model)
        elif "ESTADO_OC" in intencion_raw:
            try:
                numero = intencion_raw.split('|')[1]
                respuesta = operaciones.consultar_estado_oc(numero, db)
            except:
                respuesta = "Entendí que buscas una OC, pero no vi el número claro."
        else:
            # Charla general
            if model:
                prompt = f"Eres el asistente de Somyl. Usuario dice: '{texto_usuario}'. Responde breve."
                respuesta = safe_generate(model, prompt, default="Hola, ¿en qué puedo ayudarte?")
            else:
                respuesta = "Hola, soy el asistente virtual de Somyl. ¿En qué puedo ayudarte?"

    except Exception as e:
        logger.exception(f"Error generando respuesta: {e}")
        respuesta = "Lo siento, tuve un error interno. Intenta más tarde."

    # Asegurar texto limpio
    if not respuesta:
        respuesta = "No encontré información."
    respuesta = str(respuesta)

    # 3. Guardar traza
    try:
        INTERACTIONS.appendleft({
            'ts': int(time.time()),
            'from': telefono,
            'body': texto_usuario,
            'intent': intencion_raw,
            'response': respuesta
        })
    except: pass

    # 4. Enviar respuesta a Meta
    enviar_mensaje_meta(telefono, respuesta)