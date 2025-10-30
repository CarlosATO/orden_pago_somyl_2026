"""
Script de diagnóstico para verificar gastos de un proyecto específico
"""
import os
import sys
from pathlib import Path

# Agregar el path del backend al sys.path
backend_path = Path(__file__).parent / 'nuevo_proyecto' / 'backend'
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
from supabase import create_client

# Cargar variables de entorno desde el backend
env_file = backend_path.parent / '.env'
load_dotenv(env_file)

# Configurar Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL o SUPABASE_KEY no están configuradas")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("DIAGNÓSTICO DE GASTOS - ENTEL ARCOS LONGAVI")
print("=" * 80)

# 1. Buscar el proyecto
proyectos = supabase.table('proyectos').select('id,proyecto').ilike('proyecto', '%ARCOS%').execute()
print(f"\n📋 Proyectos encontrados con 'ARCOS':")
for p in proyectos.data:
    print(f"  - ID: {p['id']}, Nombre: {p['proyecto']}")

if not proyectos.data:
    print("❌ No se encontró el proyecto")
    exit()

proyecto_id = proyectos.data[0]['id']
proyecto_nombre = proyectos.data[0]['proyecto']
print(f"\n🎯 Analizando proyecto: {proyecto_nombre} (ID: {proyecto_id})")

# 2. Verificar órdenes de pago
print("\n" + "=" * 80)
print("ÓRDENES DE PAGO")
print("=" * 80)

ordenes = supabase.table('orden_de_pago').select('*').eq('proyecto', proyecto_id).execute()
print(f"\n📊 Total de órdenes de pago: {len(ordenes.data)}")

if ordenes.data:
    total_ordenes = 0
    items_ordenes = {}
    
    for op in ordenes.data:
        monto = op.get('costo_final_con_iva', 0) or 0
        total_ordenes += monto
        
        item = op.get('item', 'Sin item')
        mes = op.get('mes')
        
        if item not in items_ordenes:
            items_ordenes[item] = {'total': 0, 'registros': 0, 'meses': {}}
        
        items_ordenes[item]['total'] += monto
        items_ordenes[item]['registros'] += 1
        
        if mes:
            if mes not in items_ordenes[item]['meses']:
                items_ordenes[item]['meses'][mes] = 0
            items_ordenes[item]['meses'][mes] += monto
    
    print(f"\n💰 Total en órdenes de pago: ${total_ordenes:,.0f}")
    print(f"\n📋 Desglose por item:")
    for item, data in sorted(items_ordenes.items()):
        print(f"\n  {item}:")
        print(f"    Total: ${data['total']:,.0f} ({data['registros']} registros)")
        if data['meses']:
            print(f"    Por mes: {data['meses']}")
else:
    print("❌ No hay órdenes de pago para este proyecto")

# 3. Verificar gastos directos
print("\n" + "=" * 80)
print("GASTOS DIRECTOS")
print("=" * 80)

gastos = supabase.table('gastos_directos').select('*').eq('proyecto_id', proyecto_id).execute()
print(f"\n📊 Total de gastos directos: {len(gastos.data)}")

if gastos.data:
    total_gastos = 0
    items_gastos = {}
    
    # Obtener nombres de items
    items_map = {}
    for gd in gastos.data:
        item_id = gd.get('item_id')
        if item_id and item_id not in items_map:
            item_res = supabase.table('item').select('tipo').eq('id', item_id).execute()
            if item_res.data:
                items_map[item_id] = item_res.data[0].get('tipo', f'Item {item_id}')
    
    for gd in gastos.data:
        monto = gd.get('monto', 0) or 0
        total_gastos += monto
        
        item_id = gd.get('item_id')
        item_nombre = items_map.get(item_id, f'Item {item_id}')
        mes = gd.get('mes')
        
        if item_nombre not in items_gastos:
            items_gastos[item_nombre] = {'total': 0, 'registros': 0, 'meses': {}}
        
        items_gastos[item_nombre]['total'] += monto
        items_gastos[item_nombre]['registros'] += 1
        
        if mes:
            if mes not in items_gastos[item_nombre]['meses']:
                items_gastos[item_nombre]['meses'][mes] = 0
            items_gastos[item_nombre]['meses'][mes] += monto
    
    print(f"\n💰 Total en gastos directos: ${total_gastos:,.0f}")
    print(f"\n📋 Desglose por item:")
    for item, data in sorted(items_gastos.items()):
        print(f"\n  {item}:")
        print(f"    Total: ${data['total']:,.0f} ({data['registros']} registros)")
        if data['meses']:
            print(f"    Por mes: {data['meses']}")
else:
    print("❌ No hay gastos directos para este proyecto")

# 4. Total general
print("\n" + "=" * 80)
print("RESUMEN TOTAL")
print("=" * 80)

total_ordenes = sum(op.get('costo_final_con_iva', 0) or 0 for op in ordenes.data)
total_gastos = sum(gd.get('monto', 0) or 0 for gd in gastos.data)
total_general = total_ordenes + total_gastos

print(f"\nÓrdenes de pago: ${total_ordenes:,.0f}")
print(f"Gastos directos: ${total_gastos:,.0f}")
print(f"TOTAL GENERAL:   ${total_general:,.0f}")

print("\n" + "=" * 80)
print("VERIFICACIÓN DE ITEMS")
print("=" * 80)

# 5. Verificar qué items están en la tabla 'item'
items_db = supabase.table('item').select('id,tipo').execute()
print(f"\nItems disponibles en la base de datos:")
for item in items_db.data:
    print(f"  - ID {item['id']}: {item['tipo']}")

print("\n" + "=" * 80)
