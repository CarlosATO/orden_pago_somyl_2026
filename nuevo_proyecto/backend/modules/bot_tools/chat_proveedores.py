# backend/modules/bot_tools/chat_proveedores.py
import re
from flask import current_app
from .base import safe_generate, is_db_available

def procesar_consulta(texto_usuario, db, model):
    """
    Maneja TODAS las preguntas sobre proveedores.
    """
    try:
        print(f"🔎 ChatProveedores: Analizando '{texto_usuario}'")

        # 1. IDENTIFICAR QUÉ BUSCA (Nombre o Lista)
        prompt = f"""
        Analiza: "{texto_usuario}"
        - Si el usuario pide una lista general de proveedores, responde 'LISTAR'.
        - Si busca un proveedor específico, extrae SOLO el nombre limpio de la empresa.
        - Si no hay nombre claro, responde 'NONE'.
        Responde SOLO con el dato extraído.
        """
        try:
            busqueda = safe_generate(model, prompt, default=None)
            if busqueda:
                busqueda = busqueda.strip().replace('"', '').replace("'", "")
        except Exception:
            current_app.logger.exception("Error calling LLM for provider extraction")
            return "Tuve un error técnico procesando tu solicitud."

        # CASO A: No entendió el nombre
        if busqueda == "NONE" or not busqueda or len(busqueda) < 2:
            return "Entendí que preguntas por un proveedor, pero no capté el nombre. ¿Podrías repetirlo? (Ej: 'Datos de Disantel' o 'Rut de Sodimac')"

        # CASO B: Listar todos
        if busqueda == "LISTAR":
            if not is_db_available(db):
                return "No hay base de datos disponible para listar proveedores."
            res = db.table('proveedores').select('nombre').order('nombre').limit(15).execute()
            if not res.data: return "No hay proveedores registrados."
            lista = "\n".join([f"🔹 {p['nombre']}" for p in res.data])
            return f"📋 **Lista de Proveedores (Primeros 15):**\n\n{lista}\n\n_(Escribe el nombre de uno para ver su ficha)_"

        # CASO C: Buscar Proveedor Específico
        current_app.logger.info(f"👀 Buscando en DB: {busqueda}")
        res = db.table('proveedores').select('*').ilike('nombre', f'%{busqueda}%').limit(1).execute()

        if not res.data:
            return f"🚫 No encontré al proveedor *'{busqueda}'*. Intenta escribirlo diferente."

        # 2. ARMAR LA FICHA (Datos reales)
        p = res.data[0]
        
        # Limpieza de datos (para que no salga 'None')
        rut = p.get('rut', 'S/I')
        fono = p.get('fono') or p.get('telefono') or "No registrado"
        email = p.get('correo') or p.get('email') or "No registrado"
        contacto = p.get('contacto') or "Genérico"
        
        # Dirección
        dir = p.get('direccion', '')
        com = p.get('comuna', '')
        direccion_full = f"{dir}, {com}".strip(", ") or "No registrada"
        
        # Bancarios
        banco = p.get('banco') or "---"
        cuenta = p.get('cuenta') or "---"
        titular = p.get('paguese_a') or p.get('nombre')

        mensaje = f"""
🏢 **FICHA DE PROVEEDOR**
----------------------------
**{p['nombre']}**
🆔 RUT: {rut}
📍 Dirección: {direccion_full}

📞 **Contacto**
• Persona: {contacto}
• Fono: {fono}
• Email: {email}

🏦 **Datos de Pago**
• Banco: {banco}
• Cuenta: {cuenta}
• Titular: {titular}
"""
        return mensaje

    except Exception as e:
        print(f"❌ Error en ChatProveedores: {e}")
        return "Ocurrió un error consultando la base de datos."