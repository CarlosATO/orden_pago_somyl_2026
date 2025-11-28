from .base import is_db_available, safe_generate, format_money, extract_order_number

def procesar_consulta(texto_usuario, db, model=None):
    """Procesa preguntas relacionadas a pagos y ordenes de pago.
    Casos: "estado pago #", "deuda proveedor <nombre>", "pagos de la OC #"
    """
    try:
        # 1. Detectar número de orden en el texto
        oc_num = extract_order_number(texto_usuario)
        if oc_num and is_db_available(db):
            return estado_pago_por_oc(oc_num, db)

        # 2. Detectar si pregunta es por proveedor (keyword)
        if any(k in texto_usuario.lower() for k in ['proveedor', 'deuda', 'deuda total', 'saldo']):
            # intentar extraer nombre del proveedor con LLM si está disponible
            prompt = f"Extrae SOLO el nombre de proveedor del texto: '{texto_usuario}'"
            prov_name = safe_generate(model, prompt, default=None) or ''
            if not prov_name:
                # si no podemos extraer, preguntar al usuario
                return "¿Podrías indicar el nombre del proveedor? (ej: 'Deuda de Disantel')"
            return deuda_proveedor(prov_name, db)

        # 3. Pregunta genérica sobre pagos
        if 'pago' in texto_usuario.lower() or 'pagos' in texto_usuario.lower():
            return "Dime si quieres ver el estado de pago de una OC específica (ej: 'Pago OC 1234') o la deuda de un proveedor (ej: 'Deuda proveedor Disantel')"

        return "No entendí tu consulta sobre pagos. Puedes preguntar por 'Deuda proveedor XYZ' o 'Pago OC 1234'"

    except Exception as e:
        # Log en la app
        try:
            from flask import current_app
            current_app.logger.error(f"Error en chat_pagos: {e}")
        except Exception:
            pass
        return "Ocurrió un error procesando la consulta de pagos."


def estado_pago_por_oc(numero_oc, db):
    """Busca los pagos y abonos asociados a una orden de pago/orden_numero y devuelve resumen."""
    try:
        # 1. Obtener OP (ordenes de pago) por OC (orden_numero)
        res = db.table('orden_de_pago').select('*').eq('orden_numero', numero_oc).execute()
        if not res.data:
            return f"No se encontraron registros de pago para la OC #{numero_oc}."

        linhas = res.data
        total_a_pagar = sum([op.get('costo_final_con_iva', 0) or 0 for op in linhas])
        op_ids = [op.get('orden_numero') for op in linhas]

        # 2. Obtener abonos por OP
        res_ab = db.table('abonos_op').select('monto_abono').in_('orden_numero', op_ids).execute()
        total_abonado = sum([ab.get('monto_abono', 0) or 0 for ab in res_ab.data]) if res_ab.data else 0

        saldo = total_a_pagar - total_abonado
        return f"OC #{numero_oc}: Total a pagar {format_money(total_a_pagar)} - Abonado {format_money(total_abonado)} - Saldo {format_money(saldo)}"

    except Exception as e:
        try:
            from flask import current_app
            current_app.logger.exception(f"Error buscando estado de pago OC #{numero_oc}: {e}")
        except Exception:
            pass
        return "Error consultando el estado de pago de la OC."


def deuda_proveedor(nombre_proveedor, db):
    """Calcula deuda total por proveedor (suma ordenes de pago menos abonos)."""
    try:
        res_prov = db.table('proveedores').select('id, nombre, rut').ilike('nombre', f'%{nombre_proveedor}%').limit(1).execute()
        if not res_prov.data:
            return f"No encontré al proveedor '{nombre_proveedor}'"

        prov = res_prov.data[0]
        prov_id = prov['id']

        res_op = db.table('orden_de_pago').select('costo_final_con_iva, orden_numero').eq('proveedor', prov_id).execute()
        if not res_op.data:
            return f"No hay ordenes de pago registradas para {prov['nombre']}."

        total_deuda = sum([op.get('costo_final_con_iva', 0) or 0 for op in res_op.data])
        op_ids = [op['orden_numero'] for op in res_op.data]

        total_pagado = 0
        if op_ids:
            res_abonos = db.table('abonos_op').select('monto_abono').in_('orden_numero', op_ids).execute()
            total_pagado = sum([ab.get('monto_abono', 0) or 0 for ab in res_abonos.data]) if res_abonos.data else 0

        saldo = total_deuda - total_pagado
        return f"{prov['nombre']} (RUT: {prov.get('rut','N/A')}): Deuda total {format_money(total_deuda)} - Pagado {format_money(total_pagado)} - Saldo {format_money(saldo)}"

    except Exception as e:
        try:
            from flask import current_app
            current_app.logger.exception(f"Error en deuda_proveedor: {e}")
        except Exception:
            pass
        return "Error consultando la deuda del proveedor."
