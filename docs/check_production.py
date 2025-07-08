#!/usr/bin/env python3
"""
Script para verificar el entorno de producción
Ejecutar este script en el hosting para diagnosticar problemas
"""

import os
import sys

def check_environment():
    """Verifica el entorno de producción"""
    print("🔍 VERIFICACIÓN DEL ENTORNO DE PRODUCCIÓN")
    print("=" * 50)
    
    # Cargar variables de entorno
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Variables de entorno cargadas")
    except Exception as e:
        print(f"⚠️ Error cargando .env: {e}")
    
    # Verificar Python
    print(f"🐍 Python Version: {sys.version}")
    print(f"🐍 Python Executable: {sys.executable}")
    
    # Verificar variables de entorno críticas
    env_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY', 
        'SECRET_KEY'
    ]
    
    print("\n📋 Variables de Entorno:")
    missing_vars = []
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Mostrar solo los primeros caracteres por seguridad
            display_value = value[:20] + "..." if len(value) > 20 else value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: NO ENCONTRADA")
            missing_vars.append(var)
    
    # Verificar imports críticos
    print("\n📦 Imports Críticos:")
    imports_to_test = [
        ('flask', 'Flask'),
        ('supabase', 'create_client'),
        ('dotenv', 'load_dotenv'),
        ('os', None),
        ('sys', None)
    ]
    
    failed_imports = []
    for module, item in imports_to_test:
        try:
            if item:
                exec(f"from {module} import {item}")
                print(f"✅ {module}.{item}")
            else:
                exec(f"import {module}")
                print(f"✅ {module}")
        except Exception as e:
            print(f"❌ {module}: {e}")
            failed_imports.append(module)
    
    # Intentar crear la app
    print("\n🚀 Creación de la App:")
    try:
        # Agregar directorio padre al path para importar app
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, parent_dir)
        
        from app import create_app
        app = create_app()
        print("✅ App creada exitosamente")
        
        # Verificar configuración de la app
        with app.app_context():
            has_supabase = 'SUPABASE' in app.config
            print(f"✅ Supabase configurado: {'Sí' if has_supabase else 'No'}")
            
    except Exception as e:
        print(f"❌ Error creando app: {e}")
        import traceback
        traceback.print_exc()
    
    # Resumen
    print("\n" + "=" * 50)
    if missing_vars:
        print(f"❌ Variables faltantes: {', '.join(missing_vars)}")
    if failed_imports:
        print(f"❌ Imports fallidos: {', '.join(failed_imports)}")
    
    if not missing_vars and not failed_imports:
        print("🎉 ENTORNO VERIFICADO: Todo correcto")
    else:
        print("⚠️ PROBLEMAS ENCONTRADOS: Revisar arriba")

if __name__ == "__main__":
    check_environment()
