#!/usr/bin/env python3
"""
Test ajustado para encontrar el filtro exacto de fecha
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nuevo_proyecto/backend'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'nuevo_proyecto/.env'))

from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
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

# Obtener TODOS los datos
print("📥 Obteniendo datos...")
all_ingresos = []
start = 0
while True:
    response = supabase.table("ingresos").select("orden_compra, art_corr").range(start, start + 999).execute()
    rows = response.data or []
    if not rows:
        break
    all_ingresos.extend(rows)
    if len(rows) < 1000:
        break
    start += 1000

all_oc_lines = []
start = 0
while True:
    response = supabase.table("orden_de_compra").select(
        "orden_compra, fecha, total, art_corr, elimina_oc"
    ).order("orden_compra", desc=True).range(start, start + 999).execute()
    rows = response.data or []
    if not rows:
        break
    all_oc_lines.extend(rows)
    if len(rows) < 1000:
        break
    start += 1000

oc_lines_no_elim = [ln for ln in all_oc_lines if safe_str(ln.get("elimina_oc")) != ELIMINA_OC_FLAG]

ingresos_set = set()
for ing in all_ingresos:
    oc = safe_str(ing.get("orden_compra"))
    art = normalize_art_corr(ing.get("art_corr"))
    if oc:
        ingresos_set.add((oc, art))

print(f"✅ {len(all_ingresos)} ingresos, {len(oc_lines_no_elim)} líneas OC\n")

# Probar diferentes períodos de fecha
print("=" * 80)
print("🔍 PROBANDO DIFERENTES PERÍODOS DE FECHA")
print("=" * 80)

for meses in range(3, 13):
    fecha_limite = (datetime.now() - timedelta(days=meses*30)).date()
    
    oc_pendientes = {}
    total_monto = 0
    
    for ln in oc_lines_no_elim:
        oc = safe_str(ln.get("orden_compra"))
        if not oc:
            continue
        
        # Filtro por fecha
        fecha = ln.get("fecha")
        if fecha:
            try:
                if isinstance(fecha, str):
                    fecha_obj = datetime.fromisoformat(fecha.replace('Z', '+00:00')).date()
                else:
                    fecha_obj = fecha
                
                if fecha_obj < fecha_limite:
                    continue
            except:
                pass
        
        art_corr = normalize_art_corr(ln.get("art_corr"))
        clave = (oc, art_corr)
        
        if clave not in ingresos_set:
            if oc not in oc_pendientes:
                oc_pendientes[oc] = 0.0
            monto_linea = safe_float(ln.get("total"))
            oc_pendientes[oc] += monto_linea
            total_monto += monto_linea
    
    num_ocs = len(oc_pendientes)
    indicador = "🎯" if num_ocs == 31 else "  "
    print(f"{indicador} Últimos {meses:2d} meses: {num_ocs:3d} OCs, Monto total: ${total_monto:,.0f}")
    
    # Si encontramos 31, mostrar detalle
    if num_ocs == 31:
        print(f"\n✨ ¡ENCONTRADO! Con filtro de {meses} meses obtenemos 31 OCs")
        print(f"   Fecha límite: {fecha_limite}")
        print(f"   Monto total: ${total_monto:,.0f}")
        
        # Verificar si coincide con el monto de producción ($19,331,932)
        monto_produccion = 19331932
        diferencia_monto = abs(total_monto - monto_produccion)
        
        if diferencia_monto / monto_produccion < 0.01:  # Menos del 1% de diferencia
            print(f"\n🎉 ¡PERFECTO! El monto también coincide con producción")
        else:
            print(f"\n⚠️  El monto NO coincide exactamente:")
            print(f"   Producción: ${monto_produccion:,.0f}")
            print(f"   Tu sistema: ${total_monto:,.0f}")
            print(f"   Diferencia: ${diferencia_monto:,.0f}")

print("\n✅ Test completado")
