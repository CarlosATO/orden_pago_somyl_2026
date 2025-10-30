"""
Script para verificar los campos de orden_de_pago
"""
import os
from supabase import create_client
from dotenv import load_dotenv

# Cargar variables de entorno
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'nuevo_proyecto', 'backend'))
load_dotenv(os.path.join(os.path.dirname(__file__), 'nuevo_proyecto', 'backend', '.env'))

# Configurar Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# Obtener una orden de pago de ejemplo
response = supabase.table('orden_de_pago').select('*').eq('proyecto', 55).limit(3).execute()

print("\n" + "=" * 80)
print("ESTRUCTURA DE ÓRDENES DE PAGO - PROYECTO 55")
print("=" * 80)

for i, op in enumerate(response.data, 1):
    print(f"\n📄 Orden #{i}:")
    print(f"   ID: {op.get('id')}")
    print(f"   proyecto: {op.get('proyecto')}")
    print(f"   tipo: {op.get('tipo')}")
    print(f"   item: {op.get('item')}")
    print(f"   mes: {op.get('mes')}")
    print(f"   costo_final_con_iva: {op.get('costo_final_con_iva')}")
    
print("\n" + "=" * 80)
print("TODAS LAS ÓRDENES DE PAGO PARA PROYECTO 55")
print("=" * 80)

# Obtener TODAS las órdenes
all_ordenes = supabase.table('orden_de_pago').select('id, proyecto, tipo, item, mes, costo_final_con_iva').eq('proyecto', 55).execute()
print(f"\n📊 Total encontrado: {len(all_ordenes.data)} órdenes")

total = 0
for op in all_ordenes.data:
    monto = op.get('costo_final_con_iva', 0) or 0
    total += monto
    print(f"  - ID {op['id']}: {op.get('tipo') or op.get('item')} / Mes {op.get('mes')} = ${monto:,.0f}")

print(f"\n💰 TOTAL: ${total:,.0f}")
