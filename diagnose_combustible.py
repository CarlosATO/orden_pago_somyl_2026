"""
Script de diagnóstico para encontrar el gasto de COMBUSTIBLE faltante
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
    print(f"Buscando .env en: {env_file}")
    print(f"SUPABASE_URL: {SUPABASE_URL}")
    exit(1)

print(f"✅ Conectando a Supabase: {SUPABASE_URL}")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("BUSCANDO ÓRDENES DE PAGO CON COMBUSTIBLE")
print("=" * 80)

# 1. Buscar proyecto DEMO HUAWEI 2025
proyectos = supabase.table('proyectos').select('id,proyecto').ilike('proyecto', '%DEMO%HUAWEI%').execute()
print(f"\n📋 Proyectos encontrados:")
for p in proyectos.data:
    print(f"  - ID: {p['id']}, Nombre: {p['proyecto']}")

if not proyectos.data:
    print("❌ No se encontró el proyecto DEMO HUAWEI 2025")
    exit()

proyecto_id = proyectos.data[0]['id']
print(f"\n🎯 Usando proyecto ID: {proyecto_id}")

# 2. Buscar órdenes de pago con COMBUSTIBLE para ese proyecto
print(f"\n🔍 Buscando órdenes de pago con COMBUSTIBLE para proyecto {proyecto_id}...")
ordenes = supabase.table('orden_de_pago').select('*').eq('proyecto', proyecto_id).execute()

print(f"\n📊 Total de órdenes de pago para este proyecto: {len(ordenes.data)}")

# Filtrar solo las que tienen item con COMBUSTIBLE
combustibles = []
for op in ordenes.data:
    item = op.get('item', '')
    if item and 'COMBUSTIBLE' in str(item).upper():
        combustibles.append(op)

print(f"\n🔥 Órdenes con COMBUSTIBLE encontradas: {len(combustibles)}")

if combustibles:
    print("\n" + "=" * 80)
    print("DETALLE DE ÓRDENES CON COMBUSTIBLE:")
    print("=" * 80)
    for idx, op in enumerate(combustibles, 1):
        print(f"\n{idx}. Orden #{op.get('orden_numero')}")
        print(f"   Item: {op.get('item')}")
        print(f"   Mes: {op.get('mes')}")
        print(f"   Fecha factura: {op.get('fecha_factura')}")
        print(f"   Monto (costo_final_con_iva): ${op.get('costo_final_con_iva'):,.0f}")
        print(f"   Proyecto: {op.get('proyecto')}")
        print(f"   Tipo: {op.get('tipo')}")
        
        # Verificar si es abril (mes 4)
        if op.get('mes') == 4:
            print(f"   ⭐ ESTA ES LA ORDEN DE ABRIL!")
else:
    print("\n❌ NO se encontraron órdenes con COMBUSTIBLE")
    print("\n🔍 Mostrando muestra de items en las órdenes de pago:")
    items_unicos = set()
    for op in ordenes.data[:20]:  # Primeras 20
        item = op.get('item')
        if item:
            items_unicos.add(str(item))
    
    print("Items encontrados en las primeras 20 órdenes:")
    for item in sorted(items_unicos):
        print(f"  - {item}")

print("\n" + "=" * 80)
print("BUSCANDO EN GASTOS DIRECTOS...")
print("=" * 80)

# 3. Buscar en gastos_directos
gastos = supabase.table('gastos_directos').select('*').eq('proyecto_id', proyecto_id).execute()
print(f"\n📊 Total de gastos directos para este proyecto: {len(gastos.data)}")

# Buscar combustible en gastos directos
gastos_combustible = []
for gd in gastos.data:
    # Obtener el item_id y buscar el nombre
    item_id = gd.get('item_id')
    if item_id:
        item_res = supabase.table('item').select('tipo').eq('id', item_id).execute()
        if item_res.data:
            tipo = item_res.data[0].get('tipo', '')
            if 'COMBUSTIBLE' in str(tipo).upper():
                gastos_combustible.append({**gd, 'item_tipo': tipo})

print(f"\n🔥 Gastos directos con COMBUSTIBLE encontrados: {len(gastos_combustible)}")

if gastos_combustible:
    print("\n" + "=" * 80)
    print("DETALLE DE GASTOS DIRECTOS CON COMBUSTIBLE:")
    print("=" * 80)
    for idx, gd in enumerate(gastos_combustible, 1):
        print(f"\n{idx}. ID: {gd.get('id')}")
        print(f"   Item tipo: {gd.get('item_tipo')}")
        print(f"   Descripción: {gd.get('descripcion')}")
        print(f"   Mes: {gd.get('mes')}")
        print(f"   Fecha: {gd.get('fecha')}")
        print(f"   Monto: ${gd.get('monto'):,.0f}")
        
        # Verificar si es abril
        if gd.get('mes') and 'abril' in str(gd.get('mes')).lower():
            print(f"   ⭐ ESTE ES EL GASTO DE ABRIL!")
        
        # También verificar si la fecha es en abril
        fecha = gd.get('fecha')
        if fecha and '-04-' in str(fecha):
            print(f"   ⭐ LA FECHA ES DE ABRIL!")

print("\n" + "=" * 80)
