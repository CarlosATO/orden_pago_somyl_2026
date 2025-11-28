from flask import Blueprint, request, current_app
import logging
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
import os

# IMPORTAMOS EL NUEVO ESPECIALISTA
from .bot_tools import chat_proveedores, operaciones, chat_proyectos, chat_pagos, chat_ordenes, chat_materiales
from .bot_tools.base import extract_order_number, safe_generate

bp = Blueprint("chatbot", __name__)


@bp.route('/health', methods=['GET'])
def chatbot_health():
    """Return basic health info for the chatbot (modules and LLM availability)."""
    try:
        modules = ['chat_proveedores', 'chat_proyectos', 'chat_pagos', 'chat_ordenes', 'chat_materiales', 'cobranza', 'operaciones']
        return {
            'success': True,
            'llm': bool(model),
            'modules': modules
        }
    except Exception as e:
        logger.exception(f"Error in chatbot health: {e}")
        return {'success': False, 'message': str(e)}, 500

# --- CONFIGURACIÓN SEGURA ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
model = None

logger = logging.getLogger(__name__)
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        logger.info("✅ Cerebro Gemini conectado")
    except Exception as e:
        logger.error(f"❌ Error Gemini: {e}")
else:
    logger.warning("⚠️ FALTA LA CLAVE GEMINI EN RAILWAY")


def clasificar_intencion(texto):
    """Decide a qué especialista llamar.
    Uso: heurísticas (regex) primero para detectar OC o keywords; fallback LLM si necesario.
    Retorna: PROVEEDORES, PROYECTOS, ESTADO_OC|<numero>, PAGOS, o CHARLA.
    """
    # Heurísticas simples locales (fast) — evita llamadas LLM innecesarias
    oc_num = extract_order_number(texto)
    if oc_num:
        return f"ESTADO_OC|{oc_num}"

    lower = texto.lower()
    if any(k in lower for k in ['proveedor', 'proveedores', 'rut', 'fono', 'correo', 'email']):
        return 'PROVEEDORES'
    if any(k in lower for k in ['proyecto', 'obra', 'obras']):
        return 'PROYECTOS'
    if any(k in lower for k in ['deuda', 'pago', 'pagos', 'abono', 'saldo']):
        return 'PAGOS'
    if any(k in lower for k in ['orden', 'ordenes', 'oc', 'ordenes de compra', 'orden_compra', 'compra', 'compras']):
        return 'ORDENES'
    if any(k in lower for k in ['material', 'materiales', 'precio', 'stock', 'cod']):
        return 'MATERIALES'

    # Fallback LLM classification only if model configured
    if not model:
        return 'CHARLA'

    prompt = f"""
    Analiza: "{texto}"
    Clasifica en UNA categoría:
    1. PROVEEDORES: Datos de empresas, rut, pagos, contacto.
    2. PROYECTOS: Preguntas sobre obras, proyectos, faenas, gastos de un proyecto.
    3. ESTADO_OC: Estado de una orden de compra específica (N°).
    4. PAGOS: Consultas sobre pagos, abonos, saldos y ordenes de pago.
    5. CHARLA: Saludos u otros.

    Responde SOLO con: PROVEEDORES, PROYECTOS, ESTADO_OC|Numero, PAGOS, o CHARLA.
    """
    try:
        respuesta = safe_generate(model, prompt, default='CHARLA') or 'CHARLA'
        return respuesta.replace('"', '').strip()
    except Exception:
        return 'CHARLA'

@bp.route("/webhook", methods=['POST'])
def whatsapp_reply():
    db = current_app.config.get('SUPABASE')
    msg = request.values.get('Body', '')
    logger.info(f"📩 Recibido: {msg}")

    resp = MessagingResponse()
    respuesta = None

    try:
        # 1. Clasificar
        intencion_raw = clasificar_intencion(msg)
        logger.info(f"🧠 Intención: {intencion_raw}")

        # 2. Enrutar (cada módulo maneja errores internos)
        if "PROVEEDORES" in intencion_raw:
            respuesta = chat_proveedores.procesar_consulta(msg, db, model)
            logger.debug("Ruteado a chat_proveedores")
        elif "PROYECTOS" in intencion_raw:
            respuesta = chat_proyectos.procesar_consulta(msg, db, model)
            logger.debug("Ruteado a chat_proyectos")
        elif "PAGOS" in intencion_raw:
            respuesta = chat_pagos.procesar_consulta(msg, db, model)
            logger.debug("Ruteado a chat_pagos")
        elif "ORDENES" in intencion_raw:
            respuesta = chat_ordenes.procesar_consulta(msg, db, model)
            logger.debug("Ruteado a chat_ordenes")
        elif "MATERIALES" in intencion_raw:
            respuesta = chat_materiales.procesar_consulta(msg, db, model)
            logger.debug("Ruteado a chat_materiales")
        elif "ESTADO_OC" in intencion_raw:
            try:
                numero = intencion_raw.split('|')[1]
                respuesta = operaciones.consultar_estado_oc(numero, db)
                logger.debug(f"Ruteado a operaciones.consultar_estado_oc #{numero}")
            except Exception:
                respuesta = "Entendí que buscas una OC, pero no vi el número claro."
        else:
            # Charla general fallback (usar safe_generate si model existe)
            if model:
                prompt = f"Eres el asistente de Somyl. El usuario dice: '{msg}'. Responde breve y cordial."
                respuesta = safe_generate(model, prompt, default=None) or "Hola, soy el asistente virtual de Somyl. ¿En qué puedo ayudarte?"
            else:
                respuesta = "Hola, soy el asistente virtual de Somyl. ¿En qué puedo ayudarte?"

    except Exception as e:
        # Catch-all to avoid returning nothing and to ensure Twilio gets a response
        logger.exception(f"Error procesando webhook: {e}")
        respuesta = "Lo siento, ocurrió un error procesando tu solicitud. Intenta nuevamente más tarde."

    # Always respond
    try:
        resp.message(respuesta)
    except Exception:
        logger.exception("Error forming Twilio MessagingResponse; returning fallback message")
        resp.message("Lo siento, no puedo responder en este momento.")

    return str(resp)