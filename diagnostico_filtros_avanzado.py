#!/usr/bin/env python3
"""
Diagnóstico avanzado para encontrar por qué hay 192 en lugar de 31
"""

import os
import sys

# Configuración
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nuevo_proyecto/backend'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'nuevo_proyecto/.env'))

from supabase import create_client
from collections import defaultdict, Counter

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

# Obtener TODOS los ingresos
print("📥 Obteniendo TODOS los ingresos...")
all_ingresos = []
start = 0
while True:
    response = supabase.table("ingresos").select("orden_compra, art_corr, fecha").range(
        start, start + 999
    ).execute()
    rows = response.data or []
    if not rows:
        break
    all_ingresos.extend(rows)
    if len(rows) < 1000:
        break
    start += 1000

print(f"✅ Total ingresos: {len(all_ingresos)}")

# Obtener TODAS las líneas de OC
print("📥 Obteniendo TODAS las líneas de OC...")
all_oc_lines = []
start = 0
while True:
    response = supabase.table("orden_de_compra").select(
        "orden_compra, proveedor, fecha, total, art_corr, elimina_oc, proyecto"
    ).order("orden_compra", desc=True).range(
        start, start + 999
    ).execute()
    rows = response.data or []
    if not rows:
        break
    all_oc_lines.extend(rows)
    if len(rows) < 1000:
        break
    start += 1000

print(f"✅ Total líneas OC: {len(all_oc_lines)}")

# Filtrar no eliminadas
oc_lines_no_elim = [ln for ln in all_oc_lines if safe_str(ln.get("elimina_oc")) != ELIMINA_OC_FLAG]
print(f"✅ Líneas NO eliminadas: {len(oc_lines_no_elim)}\n")

# Crear set de ingresos
ingresos_set = set()
for ing in all_ingresos:
    oc = safe_str(ing.get("orden_compra"))
    art = normalize_art_corr(ing.get("art_corr"))
    if oc:
        ingresos_set.add((oc, art))

# Calcular pendientes CON diferentes filtros
print("=" * 80)
print("🔍 ANÁLISIS DE FILTROS APLICADOS")
print("=" * 80)

# 1. Sin filtro adicional (tu código actual)
oc_pendientes_sin_filtro = {}
for ln in oc_lines_no_elim:
    oc = safe_str(ln.get("orden_compra"))
    if not oc:
        continue
    art_corr = normalize_art_corr(ln.get("art_corr"))
    clave = (oc, art_corr)
    
    if clave not in ingresos_set:
        if oc not in oc_pendientes_sin_filtro:
            oc_pendientes_sin_filtro[oc] = {"monto": 0.0, "lineas": []}
        oc_pendientes_sin_filtro[oc]["monto"] += safe_float(ln.get("total"))
        oc_pendientes_sin_filtro[oc]["lineas"].append(art_corr)

print(f"\n1. Sin filtro adicional: {len(oc_pendientes_sin_filtro)} OCs pendientes")

# 2. Filtrar por fecha (ej: solo últimos 6 meses)
from datetime import datetime, timedelta
fecha_limite = (datetime.now() - timedelta(days=180)).date()

oc_pendientes_fecha = {}
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
                continue  # Saltar OCs muy antiguas
        except:
            pass
    
    art_corr = normalize_art_corr(ln.get("art_corr"))
    clave = (oc, art_corr)
    
    if clave not in ingresos_set:
        if oc not in oc_pendientes_fecha:
            oc_pendientes_fecha[oc] = {"monto": 0.0}
        oc_pendientes_fecha[oc]["monto"] += safe_float(ln.get("total"))

print(f"2. Con filtro de fecha (últimos 6 meses): {len(oc_pendientes_fecha)} OCs pendientes")

# 3. Filtrar por proyecto (solo ciertos proyectos)
# Obtener proyectos activos
print("\n🔍 Analizando proyectos...")
proyectos_counter = Counter()
for ln in oc_lines_no_elim:
    proyecto = safe_str(ln.get("proyecto"))
    if proyecto:
        proyectos_counter[proyecto] += 1

print(f"Total proyectos distintos: {len(proyectos_counter)}")
print("\nTop 10 proyectos con más líneas:")
for proyecto, count in proyectos_counter.most_common(10):
    print(f"   • Proyecto {proyecto}: {count} líneas")

# 4. Analizar fechas de las OCs pendientes
print("\n🔍 Analizando fechas de OCs pendientes...")
fechas_pendientes = []
for oc in oc_pendientes_sin_filtro.keys():
    lineas_oc = [ln for ln in oc_lines_no_elim if safe_str(ln.get("orden_compra")) == oc]
    if lineas_oc:
        fecha = lineas_oc[0].get("fecha")
        if fecha:
            try:
                if isinstance(fecha, str):
                    fecha_obj = datetime.fromisoformat(fecha.replace('Z', '+00:00')).date()
                else:
                    fecha_obj = fecha
                fechas_pendientes.append((oc, fecha_obj))
            except:
                pass

# Ordenar por fecha
fechas_pendientes.sort(key=lambda x: x[1], reverse=True)

print(f"\nTop 10 OCs pendientes más recientes:")
for i, (oc, fecha) in enumerate(fechas_pendientes[:10]):
    print(f"   {i+1}. OC {oc}: {fecha}")

print(f"\nTop 10 OCs pendientes más antiguas:")
for i, (oc, fecha) in enumerate(list(reversed(fechas_pendientes))[:10]):
    print(f"   {i+1}. OC {oc}: {fecha}")

# 5. Analizar montos
print("\n🔍 Analizando montos de OCs pendientes...")
montos_pendientes = [(oc, datos["monto"]) for oc, datos in oc_pendientes_sin_filtro.items()]
montos_pendientes.sort(key=lambda x: x[1], reverse=True)

print(f"\nTop 10 OCs pendientes con mayor monto:")
for i, (oc, monto) in enumerate(montos_pendientes[:10]):
    print(f"   {i+1}. OC {oc}: ${monto:,.0f}")

# 6. Filtrar por monto mínimo (ej: solo OCs > $100,000)
MONTO_MINIMO = 100000
oc_pendientes_monto = {
    oc: datos 
    for oc, datos in oc_pendientes_sin_filtro.items() 
    if datos["monto"] >= MONTO_MINIMO
}
print(f"\n3. Con filtro de monto mínimo (>${MONTO_MINIMO:,}): {len(oc_pendientes_monto)} OCs pendientes")

# 7. Verificar si el sistema en producción usa fecha + monto
oc_pendientes_fecha_y_monto = {
    oc: datos 
    for oc, datos in oc_pendientes_fecha.items() 
    if datos["monto"] >= MONTO_MINIMO
}
print(f"4. Con filtro de fecha Y monto: {len(oc_pendientes_fecha_y_monto)} OCs pendientes")

print("\n" + "=" * 80)
print("💡 CONCLUSIÓN")
print("=" * 80)
print(f"""
Sistema en producción: 31 OCs pendientes
Tu sistema (sin filtro): {len(oc_pendientes_sin_filtro)} OCs pendientes
Tu sistema (últimos 6 meses): {len(oc_pendientes_fecha)} OCs pendientes
Tu sistema (monto > ${MONTO_MINIMO:,}): {len(oc_pendientes_monto)} OCs pendientes
Tu sistema (fecha + monto): {len(oc_pendientes_fecha_y_monto)} OCs pendientes

La diferencia podría deberse a:
1. El sistema en producción filtra solo proyectos activos
2. Solo muestra OCs de cierto período (ej: último año)
3. Solo muestra OCs con monto significativo
4. Hay una tabla separada o caché que maneja este filtro
""")

print("\n✅ Diagnóstico completado")
