#!/usr/bin/env python3
"""
Test para verificar que el fix de paginación funciona correctamente
"""

import os
import sys

# Agregar el directorio al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nuevo_proyecto/backend'))

# Configurar variables de entorno
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'nuevo_proyecto/.env'))

# Imports necesarios
from supabase import create_client
from collections import defaultdict

# Configuración de Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Variables de entorno no configuradas")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ELIMINA_OC_FLAG = "1"

def safe_str(value):
    return str(value) if value is not None else ""

def normalize_art_corr(value):
    if value is None:
        return ""
    return str(value).strip().upper()

def safe_float(value):
    try:
        return float(value) if value else 0.0
    except (ValueError, TypeError):
        return 0.0

def get_all_ingresos_with_pagination(supabase):
    """Obtiene TODOS los ingresos con paginación"""
    all_ingresos = []
    start = 0
    page_size = 1000
    
    print("📥 Obteniendo TODOS los ingresos con paginación...")
    
    while True:
        response = supabase.table("ingresos").select("orden_compra, art_corr").range(
            start, start + page_size - 1
        ).execute()
        rows = response.data or []
        
        if not rows:
            break
        
        all_ingresos.extend(rows)
        print(f"   • Página {start//page_size + 1}: {len(rows)} registros (total acumulado: {len(all_ingresos)})")
        
        if len(rows) < page_size:
            break
        
        start += page_size
    
    print(f"✅ Total ingresos obtenidos: {len(all_ingresos)}\n")
    return all_ingresos

def get_all_oc_lines_with_pagination(supabase):
    """Obtiene TODAS las líneas de OC con paginación"""
    all_lines = []
    start = 0
    page_size = 1000
    
    print("📥 Obteniendo TODAS las líneas de OC con paginación...")
    
    while True:
        response = supabase.table("orden_de_compra").select(
            "orden_compra, proveedor, fecha, total, art_corr, elimina_oc"
        ).order("orden_compra", desc=True).range(
            start, start + page_size - 1
        ).execute()
        
        rows = response.data or []
        if not rows:
            break
        
        all_lines.extend(rows)
        print(f"   • Página {start//page_size + 1}: {len(rows)} registros (total acumulado: {len(all_lines)})")
        
        if len(rows) < page_size:
            break
        
        start += page_size
    
    print(f"✅ Total líneas OC obtenidas: {len(all_lines)}\n")
    return all_lines

print("=" * 80)
print("🧪 TEST: Verificando Fix de Paginación")
print("=" * 80)
print()

# 1. Obtener TODOS los ingresos con paginación
ingresos = get_all_ingresos_with_pagination(supabase)

# 2. Obtener TODAS las líneas de OC con paginación
oc_lines = get_all_oc_lines_with_pagination(supabase)

# 3. Filtrar eliminadas
oc_lines_no_elim = [ln for ln in oc_lines if safe_str(ln.get("elimina_oc")) != ELIMINA_OC_FLAG]
print(f"📊 Líneas NO eliminadas (elimina_oc != '1'): {len(oc_lines_no_elim)}\n")

# 4. Crear set de tuplas (oc, art_corr) de ingresos
ingresos_set = set()
for ing in ingresos:
    oc = safe_str(ing.get("orden_compra"))
    art = normalize_art_corr(ing.get("art_corr"))
    if oc:
        ingresos_set.add((oc, art))

print(f"🔑 Tuplas (OC, art_corr) únicas en ingresos: {len(ingresos_set)}\n")

# 5. Aplicar lógica: línea por línea
print("🔍 Aplicando lógica línea por línea...")
oc_pendientes = {}

for ln in oc_lines_no_elim:
    oc = safe_str(ln.get("orden_compra"))
    if not oc:
        continue
    
    art_corr = normalize_art_corr(ln.get("art_corr"))
    clave = (oc, art_corr)
    
    # Si esta línea NO está en ingresos, es pendiente
    if clave not in ingresos_set:
        if oc not in oc_pendientes:
            oc_pendientes[oc] = {
                "orden_compra": oc,
                "monto_total": 0.0,
                "lineas_pendientes": 0
            }
        oc_pendientes[oc]["monto_total"] += safe_float(ln.get("total"))
        oc_pendientes[oc]["lineas_pendientes"] += 1

print(f"✅ OCs con AL MENOS UNA línea pendiente: {len(oc_pendientes)}\n")

# 6. Calcular monto total
total_monto = sum(p["monto_total"] for p in oc_pendientes.values())

print("=" * 80)
print("📊 RESULTADO FINAL")
print("=" * 80)
print(f"✅ Total OCs pendientes: {len(oc_pendientes)}")
print(f"💰 Monto total pendiente: ${total_monto:,.0f}")
print()
print(f"🎯 Objetivo (sistema en producción): 31 órdenes")
print(f"📊 Tu código (antes del fix): 376 órdenes")
print(f"✨ Tu código (después del fix): {len(oc_pendientes)} órdenes")
print()

if len(oc_pendientes) == 31:
    print("🎉 ¡ÉXITO! El fix de paginación funciona correctamente")
    print("   El número de órdenes ahora coincide con producción")
elif len(oc_pendientes) < 376:
    print("✅ MEJORA: El número bajó considerablemente")
    print(f"   Antes: 376 → Ahora: {len(oc_pendientes)}")
    if len(oc_pendientes) != 31:
        print(f"   ⚠️  Aún hay una diferencia de {abs(len(oc_pendientes) - 31)} órdenes")
        print("   Esto podría deberse a:")
        print("   - Diferencias en los datos entre ambas bases de datos")
        print("   - Registros creados/eliminados recientemente")
        print("   - Diferencias en la lógica de filtrado de 'elimina_oc'")
else:
    print("❌ El fix NO funcionó como esperado")
    print("   Revisar la lógica de paginación y filtrado")

print("\n✅ Test completado")
