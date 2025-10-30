#!/usr/bin/env python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nuevo_proyecto', 'backend'))

from app import create_app

app = create_app()
client = app.config['SUPABASE']

print("\n" + "=" * 80)
print("VERIFICACIÓN DE ÓRDENES DE PAGO - PROYECTO 55 (ENTEL ARCOS LONGAVÍ)")
print("=" * 80)

result = client.table('orden_de_pago').select('*').eq('proyecto', 55).execute()

print(f"\n📊 Total de órdenes: {len(result.data)}")

total = 0
for op in result.data:
    monto = op.get('costo_final_con_iva', 0) or 0
    total += monto
    print(f"\nID {op['id']}:")
    print(f"  tipo: {op.get('tipo')}")
    print(f"  item: {op.get('item')}")
    print(f"  mes: {op.get('mes')}")
    print(f"  costo_final_con_iva: ${monto:,.0f}")

print(f"\n💰 TOTAL: ${total:,.0f}")
print("\n" + "=" * 80)
