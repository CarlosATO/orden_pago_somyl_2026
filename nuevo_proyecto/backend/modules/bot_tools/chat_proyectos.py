# backend/modules/bot_tools/chat_proyectos.py
import re

def procesar_consulta(texto_usuario, db, model):
    """
    Maneja preguntas sobre PROYECTOS (Obras).
    """
    try:
        print(f"🏗️ ChatProyectos: Analizando '{texto_usuario}'")

        # 1. IDENTIFICAR INTENCIÓN CON IA
        prompt = f"""
        Analiza: "{texto_usuario}"
        - Si pide listar proyectos activos/obras, responde 'LISTAR'.
        - Si busca un proyecto específico, extrae SOLO el nombre o palabra clave.
        - Si no hay nombre claro, responde 'NONE'.
        Responde SOLO con el dato extraído.
        """
        try:
            busqueda = model.generate_content(prompt).text.strip().replace('"', '').replace("'", "")
        except:
            return "Tuve un error técnico analizando el nombre del proyecto."

        if busqueda == "NONE" or len(busqueda) < 2:
            return "Entendí que buscas un Proyecto, pero no capté el nombre. (Ej: 'Estado del proyecto Torre B' o 'Lista de obras')"

        # CASO A: LISTAR PROYECTOS ACTIVOS
        if busqueda == "LISTAR":
            # Asumimos que tienes una columna 'activo' o similar. Si no, quitamos el filtro.
            res = db.table('proyectos').select('proyecto').eq('activo', True).limit(15).execute()
            if not res.data: return "No hay proyectos activos registrados."
            
            lista = "\n".join([f"🏗️ {p['proyecto']}" for p in res.data])
            return f"📋 **Proyectos Activos:**\n\n{lista}\n\n_(Escribe el nombre de uno para ver su estado financiero)_"

        # CASO B: BUSCAR UN PROYECTO ESPECÍFICO
        print(f"👀 Buscando Proyecto: {busqueda}")
        res = db.table('proyectos').select('*').ilike('proyecto', f'%{busqueda}%').limit(1).execute()

        if not res.data:
            return f"🚫 No encontré ningún proyecto que coincida con *'{busqueda}'*."

        p = res.data[0]
        p_id = p['id']

        # --- EL SUPERPODER: CÁLCULO FINANCIERO EN TIEMPO REAL ---
        # Sumamos todas las Órdenes de Compra de este proyecto
        gastos = db.table('orden_de_compra').select('total').eq('proyecto', p_id).execute()
        
        total_gastado = sum([g.get('total', 0) or 0 for g in gastos.data])
        cantidad_ocs = len(gastos.data)
        
        # Formato moneda
        total_fmt = "${:,.0f}".format(total_gastado).replace(",", ".")
        
        # Datos generales
        cliente = p.get('cliente', 'Interno')
        direccion = p.get('direccion', 'Sin dirección')
        estado = "🟢 Activo" if p.get('activo') else "🔴 Cerrado"

        mensaje = f"""
🏗️ **FICHA DE PROYECTO**
----------------------------
**{p['proyecto']}**
📍 {direccion}
👤 Cliente: {cliente}
Estado: {estado}

💰 **Estado Financiero**
• Gasto Comprometido: *{total_fmt}*
• Órdenes Emitidas: {cantidad_ocs}

_(Este monto es la suma de todas las OCs emitidas para esta obra)_
"""
        return mensaje

    except Exception as e:
        print(f"❌ Error en ChatProyectos: {e}")
        return "Ocurrió un error consultando el proyecto."