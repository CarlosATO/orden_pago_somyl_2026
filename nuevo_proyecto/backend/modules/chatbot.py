from flask import Blueprint, request, current_app
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
import os

# IMPORTAMOS EL NUEVO ESPECIALISTA
from .bot_tools import chat_proveedores, operaciones

bp = Blueprint("chatbot", __name__)

# --- CONFIGURACIÓN SEGURA ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
model = None

if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        print("✅ Cerebro Gemini conectado")
    except Exception as e:
        print(f"❌ Error Gemini: {e}")
else:
    print("⚠️ FALTA LA CLAVE GEMINI EN RAILWAY")


def clasificar_intencion(texto):
    """Decide a qué especialista llamar"""
    if not model: return "ERROR"
    
    prompt = f"""
    Analiza: "{texto}"
    Clasifica en UNA categoría:
    1. PROVEEDORES: Si pide datos, rut, banco, contacto o lista de empresas.
    2. ESTADO_OC: Si pide estado de una orden de compra (OC). Extrae el número. (Ej: ESTADO_OC|3520)
    3. CHARLA: Saludos o cualquier otra cosa.
    
    Responde SOLO formato: CATEGORIA o CATEGORIA|DATO
    """
    try:
        return model.generate_content(prompt).text.strip().replace('"', '')
    except:
        return "CHARLA"

@bp.route("/webhook", methods=['POST'])
def whatsapp_reply():
    db = current_app.config['SUPABASE']
    msg = request.values.get('Body', '')
    print(f"📩 Recibido: {msg}")

    # 1. Clasificar
    intencion_raw = clasificar_intencion(msg)
    print(f"🧠 Intención: {intencion_raw}")

    resp = MessagingResponse()
    respuesta = ""

    # 2. Enrutar
    if "PROVEEDORES" in intencion_raw:
        respuesta = chat_proveedores.procesar_consulta(msg, db, model)

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