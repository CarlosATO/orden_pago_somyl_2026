from datetime import datetime
from flask import current_app
from .base import format_date_iso

def formatear_fecha(fecha_str):
    # wrapper: prefer base.format_date_iso but keep local name
    return format_date_iso(fecha_str)

def consultar_estado_oc(numero_oc, db):
    """
    Busca una OC forzando el tipo de dato a ENTERO.
    """
    try:
        current_app.logger.info(f"🔍 Buscando OC #{numero_oc}")
        
        # --- CORRECCIÓN CRÍTICA: Forzar conversión a int ---
        try:
            numero_limpio = int(str(numero_oc).strip())
        except ValueError:
            return f"El valor '{numero_oc}' no parece un número de orden válido."
        
        # 1. Buscar Header
        res_oc = db.table('orden_de_compra').select('*').eq('orden_compra', numero_limpio).execute()
        
        if not res_oc.data:
            return f"🚫 La Orden de Compra #{numero_limpio} no aparece en la base de datos activa."

        lineas = res_oc.data
        primera = lineas[0]
        
        # 2. Datos Generales
        fecha = formatear_fecha(primera.get('fecha'))
        proveedor_id = primera.get('proveedor')
        proyecto_id = primera.get('proyecto')
        
        nom_prov = "Desconocido"
        if proveedor_id:
            try:
                p = db.table('proveedores').select('nombre').eq('id', proveedor_id).single().execute()
                if p.data: nom_prov = p.data['nombre']
            except: pass

        nom_proy = "Sin Proyecto"
        if proyecto_id:
            try:
                pr = db.table('proyectos').select('proyecto').eq('id', proyecto_id).single().execute()
                if pr.data: nom_proy = pr.data['proyecto']
            except: pass

        # 3. Detalle Items
        detalle_txt = ""
        for item in lineas[:8]: # Mostrar máx 8 líneas
            # Buscamos el nombre en varios campos posibles
            desc = item.get('descripcion') or item.get('detalle') or item.get('material') or "Ítem"
            cant = item.get('cantidad', 0)
            detalle_txt += f"• {cant} x {desc}\n"
            
        if len(lineas) > 8:
            detalle_txt += f"... y {len(lineas)-8} más."

        # 4. Calcular Estado (Recepciones)
        res_ing = db.table('ingresos').select('cantidad_ingresada').eq('orden_compra', numero_limpio).execute()
        
        total_solicitado = sum([l.get('cantidad', 0) for l in lineas])
        total_recibido = sum([i.get('cantidad_ingresada', 0) for i in res_ing.data])
        
        estado = "🔴 PENDIENTE"
        if total_recibido > 0:
            if total_recibido >= total_solicitado:
                estado = "🟢 COMPLETADA"
            else:
                estado = "🟡 PARCIAL"

        return f"""
📄 *ORDEN #{numero_limpio}*
📅 {fecha} | {estado}
🏢 {nom_prov}
🏗️ {nom_proy}

📦 *Detalle:*
{detalle_txt}
"""

    except Exception as e:
        current_app.logger.exception(f"❌ Error tool OC: {e}")
        return "Error técnico consultando la orden."