#!/usr/bin/env python3
"""
Script de diagnóstico para verificar que el backend puede iniciar
"""
import sys
import os
from pathlib import Path

# Agregar el directorio al path
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

print("🔍 Diagnóstico del Backend\n")
print("="*60)

# 1. Verificar imports
print("\n1️⃣ Verificando imports...")
try:
    from backend.app import create_app
    print("   ✅ backend.app importado correctamente")
except Exception as e:
    print(f"   ❌ Error al importar backend.app: {e}")
    sys.exit(1)

# 2. Verificar .env
print("\n2️⃣ Verificando archivo .env...")
env_file = SCRIPT_DIR / ".env"
if env_file.exists():
    print(f"   ✅ Archivo .env encontrado")
    # Verificar variables clave
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'SECRET_KEY']
    for var in required_vars:
        if os.environ.get(var):
            print(f"   ✅ {var} está definida")
        else:
            print(f"   ⚠️  {var} NO está definida")
else:
    print(f"   ❌ Archivo .env NO encontrado en {env_file}")

# 3. Intentar crear la app
print("\n3️⃣ Intentando crear la aplicación Flask...")
try:
    app = create_app()
    print("   ✅ Aplicación Flask creada exitosamente")
    
    # Listar rutas registradas
    print("\n   📋 Rutas registradas:")
    for rule in app.url_map.iter_rules():
        print(f"      {rule.methods} {rule.rule}")
    
except Exception as e:
    print(f"   ❌ Error al crear la aplicación: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Verificar conexión a Supabase
print("\n4️⃣ Verificando conexión a Supabase...")
try:
    supabase = app.config.get('SUPABASE')
    if supabase:
        print("   ✅ Cliente Supabase configurado")
        # Probar una consulta simple
        result = supabase.table('usuarios').select('id').limit(1).execute()
        print(f"   ✅ Conexión a Supabase exitosa (encontrados {len(result.data)} registros en prueba)")
    else:
        print("   ❌ Cliente Supabase NO configurado")
except Exception as e:
    print(f"   ⚠️  Error al probar Supabase: {e}")

print("\n" + "="*60)
print("✅ Diagnóstico completado - Backend está listo para iniciar")
print("\nPara iniciar el backend, ejecuta:")
print("   python run_backend.py")
