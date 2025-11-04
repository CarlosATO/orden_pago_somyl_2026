#!/usr/bin/env python3
"""
Diagnóstico de OCs no recepcionadas - Compara lógica actual con producción
"""

import os
import sys

# Agregar el directorio al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nuevo_proyecto/backend'))

# Configurar variables de entorno si es necesario
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
    print("Asegúrate de tener SUPABASE_URL y SUPABASE_ANON_KEY en tu .env")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ELIMINA_OC_FLAG = "1"

def safe_str(value):
    return str(value) if value is not None else ""

def normalize_art_corr(value):
    if value is None:
        return ""
    return str(value).strip().upper()

print("=" * 80)
print("📊 DIAGNÓSTICO DE ÓRDENES NO RECEPCIONADAS")
print("=" * 80)

# 1. Obtener todas las líneas de orden_de_compra
print("\n1️⃣ Obteniendo líneas de orden_de_compra...")
oc_response = supabase.table("orden_de_compra").select(
    "orden_compra, proveedor, total, art_corr, elimina_oc"
).order("orden_compra", desc=True).execute()

oc_lines = oc_response.data or []
print(f"   ✅ Total líneas: {len(oc_lines)}")

# 2. Filtrar eliminadas
oc_lines_no_elim = [ln for ln in oc_lines if safe_str(ln.get("elimina_oc")) != ELIMINA_OC_FLAG]
print(f"   ✅ Líneas NO eliminadas (elimina_oc != '1'): {len(oc_lines_no_elim)}")

# 3. Contar OCs únicas
ocs_unicas = set(safe_str(ln["orden_compra"]) for ln in oc_lines_no_elim if ln.get("orden_compra"))
print(f"   ✅ OCs únicas (no eliminadas): {len(ocs_unicas)}")

# 4. Obtener todos los ingresos
print("\n2️⃣ Obteniendo ingresos...")
ingresos_response = supabase.table("ingresos").select("orden_compra, art_corr").execute()
ingresos = ingresos_response.data or []
print(f"   ✅ Total ingresos: {len(ingresos)}")

# 5. Crear set de tuplas (oc, art_corr) de ingresos
ingresos_set = set()
for ing in ingresos:
    oc = safe_str(ing.get("orden_compra"))
    art = normalize_art_corr(ing.get("art_corr"))
    if oc:
        ingresos_set.add((oc, art))

print(f"   ✅ Tuplas (OC, art_corr) únicas en ingresos: {len(ingresos_set)}")

# 6. Aplicar LÓGICA DEL SISTEMA ANTIGUO (línea por línea)
print("\n3️⃣ Aplicando lógica del sistema antiguo (línea por línea)...")
oc_pendientes_antiguo = {}

for ln in oc_lines_no_elim:
    oc = safe_str(ln.get("orden_compra"))
    if not oc:
        continue
    
    art_corr = normalize_art_corr(ln.get("art_corr"))
    clave = (oc, art_corr)
    
    # Si esta línea NO está en ingresos, es pendiente
    if clave not in ingresos_set:
        if oc not in oc_pendientes_antiguo:
            oc_pendientes_antiguo[oc] = {
                "orden_compra": oc,
                "monto_total": 0.0,
                "lineas_pendientes": []
            }
        oc_pendientes_antiguo[oc]["monto_total"] += float(ln.get("total") or 0)
        oc_pendientes_antiguo[oc]["lineas_pendientes"].append(art_corr)

print(f"   ✅ OCs con AL MENOS UNA línea pendiente: {len(oc_pendientes_antiguo)}")

# 7. Mostrar ejemplos
print("\n4️⃣ Ejemplos de OCs pendientes (primeras 10):")
for i, (oc, datos) in enumerate(list(oc_pendientes_antiguo.items())[:10]):
    lineas_count = len(datos["lineas_pendientes"])
    monto = datos["monto_total"]
    print(f"   {i+1}. OC {oc}: {lineas_count} líneas pendientes, Monto: ${monto:,.0f}")

# 8. Comparar con OCs que tienen TODAS las líneas recibidas
print("\n5️⃣ Verificando OCs completamente recibidas...")
oc_con_ingresos = defaultdict(set)
for ing in ingresos:
    oc = safe_str(ing.get("orden_compra"))
    art = normalize_art_corr(ing.get("art_corr"))
    if oc:
        oc_con_ingresos[oc].add(art)

ocs_completas = []
ocs_parciales = []

for oc in ocs_unicas:
    # Obtener todas las líneas de esta OC
    lineas_oc = [ln for ln in oc_lines_no_elim if safe_str(ln.get("orden_compra")) == oc]
    art_corrs_oc = set(normalize_art_corr(ln.get("art_corr")) for ln in lineas_oc)
    
    # Ver cuántas se han recibido
    art_corrs_recibidos = oc_con_ingresos.get(oc, set())
    
    if art_corrs_recibidos >= art_corrs_oc:
        ocs_completas.append(oc)
    elif len(art_corrs_recibidos) > 0:
        ocs_parciales.append(oc)

print(f"   ✅ OCs completamente recibidas: {len(ocs_completas)}")
print(f"   ⚠️  OCs parcialmente recibidas: {len(ocs_parciales)}")
print(f"   📦 OCs sin ningún ingreso: {len(ocs_unicas) - len(ocs_completas) - len(ocs_parciales)}")

# 9. Resumen final
print("\n" + "=" * 80)
print("📊 RESUMEN FINAL")
print("=" * 80)
print(f"✅ OCs pendientes (con AL MENOS UNA línea sin recibir): {len(oc_pendientes_antiguo)}")
print(f"✅ OCs completamente recibidas: {len(ocs_completas)}")
print(f"⚠️  OCs parcialmente recibidas: {len(ocs_parciales)}")
print(f"📦 OCs sin ningún ingreso: {len(ocs_unicas) - len(ocs_completas) - len(ocs_parciales)}")
print()
print(f"💡 El sistema en producción muestra: 31 órdenes")
print(f"💡 Tu código actual muestra: {len(oc_pendientes_antiguo)} órdenes")
print()

# 10. Identificar la discrepancia
if len(oc_pendientes_antiguo) == 376:
    print("⚠️  PROBLEMA IDENTIFICADO:")
    print("    El código está mostrando TODAS las OCs que tienen alguna línea no recibida.")
    print("    Posibles causas:")
    print("    1. El campo 'art_corr' no se está normalizando correctamente")
    print("    2. La comparación (oc, art_corr) no está matcheando correctamente")
    print("    3. Hay un problema con el filtro de 'elimina_oc'")
    print()
    
    # Verificar normalización de art_corr
    print("🔍 Verificando normalización de art_corr...")
    sample_ocs = list(ocs_unicas)[:5]
    for oc in sample_ocs:
        lineas = [ln for ln in oc_lines_no_elim if safe_str(ln.get("orden_compra")) == oc]
        ingresos_oc = [ing for ing in ingresos if safe_str(ing.get("orden_compra")) == oc]
        
        print(f"\n   OC {oc}:")
        print(f"   - Líneas en orden_de_compra: {len(lineas)}")
        for ln in lineas[:3]:
            art = ln.get("art_corr")
            norm = normalize_art_corr(art)
            print(f"     • art_corr: '{art}' → normalizado: '{norm}'")
        
        print(f"   - Ingresos: {len(ingresos_oc)}")
        for ing in ingresos_oc[:3]:
            art = ing.get("art_corr")
            norm = normalize_art_corr(art)
            print(f"     • art_corr: '{art}' → normalizado: '{norm}'")

print("\n✅ Diagnóstico completado")
