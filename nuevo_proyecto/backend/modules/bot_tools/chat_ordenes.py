from .base import extract_order_number, is_db_available, format_money, format_date_iso, safe_generate
from flask import current_app

def procesar_consulta(texto_usuario, db, model=None):
    """Responde preguntas relacionadas a órdenes de compra: detalle, estado, pdf.
    Ejemplos:
      - "Detalle OC 1234"
      - "Estado orden 1234"
      - "Mostrar PDF OC 1234"
    """
    try:
        oc_num = extract_order_number(texto_usuario)
        if oc_num and is_db_available(db):
            return detalle_oc(oc_num, db)

        # Pregunta por listado para proveedor
        if 'proveedor' in (texto_usuario or '').lower() and is_db_available(db):
            prompt = f"Extrae SOLO el nombre del proveedor de: '{texto_usuario}'"
            prov_name = safe_generate(model, prompt, default=None) or ''
            if not prov_name:
                return "Indica el nombre del proveedor para listar sus órdenes."
            # Buscar proveedor y listar OCs
            res_prov = db.table('proveedores').select('id,nombre').ilike('nombre', f'%{prov_name}%').limit(1).execute()
            if not res_prov.data:
                return f"No encontré al proveedor '{prov_name}'"
            prov = res_prov.data[0]
            res_ocs = db.table('orden_de_compra').select('orden_compra, fecha, total').eq('proveedor', prov['id']).order('fecha', desc=True).limit(10).execute()
            if not res_ocs.data:
                return f"No hay OC registradas para {prov['nombre']}"
            lines = [f"OC {o['orden_compra']} | {format_date_iso(o.get('fecha'))} | {format_money(o.get('total'))}" for o in res_ocs.data]
            return f"Órdenes para {prov['nombre']}:\n" + "\n".join(lines)

        return "Puedo ayudarte con el detalle de una OC (ej: 'OC 1234') o listar OCs de un proveedor (ej: 'Órdenes proveedor Disantel')."

    except Exception as e:
        current_app.logger.exception(f"Error en chat_ordenes: {e}")
        return "Error consultando órdenes."


def detalle_oc(numero_oc, db):
    try:
        res = db.table('orden_de_compra').select('*').eq('orden_compra', numero_oc).execute()
        if not res.data:
            return f"OC #{numero_oc} no encontrada."
        rows = res.data
        header = rows[0]
        fecha = format_date_iso(header.get('fecha'))
        prov = 'Desconocido'
        try:
            p = db.table('proveedores').select('nombre').eq('id', header.get('proveedor')).single().execute()
            if p.data: prov = p.data.get('nombre')
        except: pass
        total = sum([float(r.get('total', 0) or 0) for r in rows])
        lines_txt = '\n'.join([f"• {int(l.get('cantidad',0))} x {l.get('descripcion','Ítem')}" for l in rows[:8]])
        if len(rows) > 8:
            lines_txt += f"\n... y {len(rows)-8} más."

        pdf_link = f"/api/ordenes/{numero_oc}/pdf"
        return f"OC #{numero_oc} | {fecha} | {prov}\nTotal: {format_money(total)}\n{lines_txt}\nPDF: {pdf_link}"
    except Exception as e:
        current_app.logger.exception(f"Error detalle_oc {e}")
        return "Error consultando la OC."
