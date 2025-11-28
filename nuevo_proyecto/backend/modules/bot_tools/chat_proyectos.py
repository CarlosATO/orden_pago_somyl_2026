import re
from flask import current_app
from .base import safe_generate, is_db_available, format_money

def procesar_consulta(texto_usuario, db, model):
    """
    Maneja preguntas sobre PROYECTOS (Obras) con búsqueda inteligente.
    """
    try:
        print(f"🏗️ ChatProyectos: Analizando '{texto_usuario}'")

        # 1. ESTRATEGIA DE EXTRACCIÓN (Prompt Mejorado)
        prompt = f"""
        Tu trabajo es extraer el nombre del proyecto de construcción de este mensaje: "{texto_usuario}"
        
        Reglas:
        1. Si pide lista (ej: "ver obras", "cuales son los proyectos"), responde 'LISTAR'.
        2. Si pregunta por una obra (ej: "gastos de Borgoño", "estado financiero Huawei"), extrae SOLO el nombre (ej: "Borgoño", "Huawei").
        3. IGNORA palabras de relleno como: estado, financiero, dame, gasto, informe, proyecto, obra.
        4. Si no hay nombre, responde 'NONE'.
        
        Responde SOLO con el dato extraído.
        """
        try:
            busqueda = safe_generate(model, prompt, default='NONE')
            if busqueda:
                busqueda = busqueda.strip().replace('"', '').replace("'", "")
        except Exception:
            current_app.logger.exception("Error calling LLM for project extraction")
            busqueda = 'NONE'

        # CASO A: LISTAR PROYECTOS
        if busqueda == "LISTAR":
            if not is_db_available(db):
                return "No hay base de datos disponible para listar proyectos."
            res = db.table('proyectos').select('proyecto').eq('activo', True).limit(20).execute()
            if not res.data: return "No hay proyectos activos."
            
            lista = "\n".join([f"🏗️ {p['proyecto']}" for p in res.data])
            return f"📋 **Proyectos Activos:**\n\n{lista}\n\n_(Escribe el nombre de uno para ver sus finanzas)_"

        # CASO B: BÚSQUEDA POR NOMBRE (Con Respaldo)
        # Si la IA falló (NONE) o nos dio algo muy corto, usamos la "palabra clave"
        palabra_clave = busqueda
        
        if busqueda == "NONE" or not busqueda or len(busqueda) < 2:
            # PLAN B: Tomamos la palabra más larga de la frase del usuario
            # (Ej: "dame estado BORGOÑO" -> "BORGOÑO")
            palabras = texto_usuario.split()
            palabras_utiles = [p for p in palabras if len(p) > 3 and p.lower() not in ['dame', 'estado', 'financiero', 'proyecto', 'lista']]
            if palabras_utiles:
                palabra_clave = max(palabras_utiles, key=len)
                current_app.logger.info(f"🔄 IA falló, intentando con palabra clave: '{palabra_clave}'")
            else:
                return "Entendí que buscas un Proyecto, pero no capté el nombre. (Ej: 'Estado Borgoño')"

        current_app.logger.info(f"👀 Buscando Proyecto: '{palabra_clave}'")
        
        # Buscamos en la base de datos
        if not is_db_available(db):
            return "No hay base de datos disponible para buscar proyectos."
        res = db.table('proyectos').select('*').ilike('proyecto', f'%{palabra_clave}%').limit(1).execute()

        if not res.data:
            return f"🚫 No encontré el proyecto *'{palabra_clave}'*.\nPrueba escribiendo solo una parte del nombre."

        p = res.data[0]
        p_id = p['id']

        # --- CÁLCULO FINANCIERO ---
        # Sumamos todas las Órdenes de Compra
        gastos = db.table('orden_de_compra').select('total').eq('proyecto', p_id).execute()
        total_gastado = sum([float(g.get('total', 0) or 0) for g in (gastos.data or [])])
        cantidad_ocs = len(gastos.data)
        
        total_fmt = format_money(total_gastado)
        
        cliente = p.get('cliente', 'Interno')
        direccion = p.get('direccion') or "Sin dirección"
        estado_obra = "🟢 Activo" if p.get('activo') else "🔴 Cerrado"

        return f"""
🏗️ **REPORTE DE OBRA**
----------------------------
**{p['proyecto']}**
📍 {direccion}
👤 Cliente: {cliente}
Estado: {estado_obra}

💰 **Finanzas (Gastos)**
• Total Comprometido: *{total_fmt}*
• N° de Órdenes: {cantidad_ocs}
"""

    except Exception as e:
        current_app.logger.exception(f"❌ Error en ChatProyectos: {e}")
        return "Ocurrió un error consultando el proyecto."