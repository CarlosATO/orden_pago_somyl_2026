#!/usr/bin/env python3
"""
Script para diagnosticar la estructura de la tabla presupuesto
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Cargar variables de entorno
load_dotenv('/Users/carlosalegria/Desktop/Migracion_OP/nuevo_proyecto/.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: Variables de entorno no configuradas")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🔍 Diagnóstico de tabla 'presupuesto'\n")

# Intentar obtener un registro de muestra
try:
    result = supabase.table("presupuesto").select("*").limit(1).execute()
    
    if result.data and len(result.data) > 0:
        registro = result.data[0]
        print("✅ Estructura de la tabla (campos encontrados):")
        print("-" * 50)
        for campo, valor in registro.items():
            tipo = type(valor).__name__
            print(f"  • {campo}: {tipo} = {valor}")
    else:
        print("⚠️  No hay registros en la tabla para ver estructura")
        print("Intentando insertar un registro de prueba...")
        
        # Intentar insertar con campos mínimos
        test_data = {
            "proyecto_id": 1,
            "item": "TEST",
            "fecha": "2025-11-05",
            "monto": 1000
        }
        
        try:
            insert_result = supabase.table("presupuesto").insert(test_data).execute()
            print(f"✅ Inserción exitosa con campos mínimos")
            print(f"Resultado: {insert_result.data}")
        except Exception as e:
            print(f"❌ Error al insertar: {e}")
            print("\nProbablemente faltan campos obligatorios.")
            
except Exception as e:
    print(f"❌ Error al consultar tabla: {e}")
    print("\nDetalles del error:")
    print(str(e))
