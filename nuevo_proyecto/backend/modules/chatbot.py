from flask import Blueprint, request, current_app
import logging
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
import os

# IMPORTAMOS EL NUEVO ESPECIALISTA
from .bot_tools import chat_proveedores, operaciones, chat_proyectos, chat_pagos, chat_ordenes, chat_materiales
from .bot_tools.base import extract_order_number, safe_generate

bp = Blueprint("chatbot", __name__)

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
    if any(k in lower for k in ['orden', 'ordenes', 'oc', 'ordenes de compra', 'orden_compra']):
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
    db = current_app.config['SUPABASE']
    msg = request.values.get('Body', '')
    logger.info(f"📩 Recibido: {msg}")

    # 1. Clasificar
    intencion_raw = clasificar_intencion(msg)
    logger.info(f"🧠 Intención: {intencion_raw}")

    resp = MessagingResponse()
    respuesta = ""

    # 2. Enrutar
    if "PROVEEDORES" in intencion_raw:
        respuesta = chat_proveedores.procesar_consulta(msg, db, model)
    
    elif "PROYECTOS" in intencion_raw:
        respuesta = chat_proyectos.procesar_consulta(msg, db, model)
    elif "PAGOS" in intencion_raw:
        respuesta = chat_pagos.procesar_consulta(msg, db, model)

    elif "ORDENES" in intencion_raw:
        respuesta = chat_ordenes.procesar_consulta(msg, db, model)

    elif "MATERIALES" in intencion_raw:
        respuesta = chat_materiales.procesar_consulta(msg, db, model)

    elif "ESTADO_OC" in intencion_raw:
        try:
            numero = intencion_raw.split('|')[1]
            respuesta = operaciones.consultar_estado_oc(numero, db)
        except:
            respuesta = "Entendí que buscas una OC, pero no vi el número claro."

    else:
        # Charla general
        try:
            prompt = f"Eres el asistente de Somyl. El usuario dice: '{msg}'. Responde breve y cordial."
            respuesta = model.generate_content(prompt).text
        except:
            respuesta = "Hola, soy el asistente virtual de Somyl. ¿En qué puedo ayudarte?"

    resp.message(respuesta)
    return str(resp)