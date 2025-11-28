# backend/modules/bot_tools/cobranza.py

def consultar_deuda_proveedor(nombre_proveedor, db):
    """
    Busca proveedor por nombre y calcula deuda.
    """
    try:
        print(f"🔍 Herramienta Cobranza: Buscando '{nombre_proveedor}'")
        
        # 1. Buscar ID
        res_prov = db.table('proveedores').select('id, nombre, rut').ilike('nombre', f'%{nombre_proveedor}%').limit(1).execute()
        if not res_prov.data:
            return None
        
        prov = res_prov.data[0]
        
        # 2. Calcular deuda
        res_op = db.table('orden_de_pago').select('costo_final_con_iva, orden_numero').eq('proveedor', prov['id']).execute()
        total_deuda = sum([op.get('costo_final_con_iva', 0) or 0 for op in res_op.data])
        
        # 3. Calcular pagos
        op_ids = [op['orden_numero'] for op in res_op.data]
        total_pagado = 0
        if op_ids:
            res_abonos = db.table('abonos_op').select('monto_abono').in_('orden_numero', op_ids).execute()
            total_pagado = sum([ab.get('monto_abono', 0) or 0 for ab in res_abonos.data])
            
        saldo = total_deuda - total_pagado
        saldo_fmt = "${:,.0f}".format(saldo).replace(",", ".")
        
        return f"""
        🏢 *{prov['nombre']}* (RUT: {prov['rut']})
        💰 Deuda Total: *{saldo_fmt}*
        """
    except Exception as e:
        print(f"❌ Error en tool_cobranza: {e}")
        return None