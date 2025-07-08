#!/usr/bin/env python3
"""
Script de diagnóstico para identificar errores en la aplicación
"""

import sys
import traceback

def test_basic_imports():
    """Prueba imports básicos"""
    try:
        print("1. Probando import os...")
        import os
        print("✅ os importado correctamente")
        
        print("2. Probando import flask...")
        from flask import Flask
        print("✅ Flask importado correctamente")
        
        print("3. Probando import supabase...")
        from supabase import create_client
        print("✅ Supabase importado correctamente")
        
        print("4. Probando import dotenv...")
        from dotenv import load_dotenv
        print("✅ dotenv importado correctamente")
        
        return True
    except Exception as e:
        print(f"❌ Error en imports básicos: {e}")
        traceback.print_exc()
        return False

def test_environment():
    """Prueba variables de entorno"""
    try:
        print("5. Cargando variables de entorno...")
        from dotenv import load_dotenv
        load_dotenv()
        
        import os
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if supabase_url and supabase_key:
            print("✅ Variables de entorno encontradas")
            print(f"   SUPABASE_URL: {supabase_url[:50]}...")
            print(f"   SUPABASE_ANON_KEY: {supabase_key[:20]}...")
        else:
            print("⚠️ Variables de entorno no encontradas")
            print(f"   SUPABASE_URL: {supabase_url}")
            print(f"   SUPABASE_ANON_KEY: {'Found' if supabase_key else 'Not found'}")
        
        return True
    except Exception as e:
        print(f"❌ Error en variables de entorno: {e}")
        traceback.print_exc()
        return False

def test_app_modules():
    """Prueba imports de módulos de la app"""
    try:
        print("6. Probando import de módulos de la app...")
        
        # Agregar directorio padre al path para importar app
        import os
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, parent_dir)
        
        print("   - app.modules.usuarios...")
        from app.modules.usuarios import get_modulos_usuario
        print("   ✅ usuarios importado")
        
        print("   - app.utils.cache...")
        from app.utils.cache import cache
        print("   ✅ cache importado")
        
        print("   - app.utils.api_helpers...")
        from app.utils.api_helpers import api_cache
        print("   ✅ api_helpers importado")
        
        return True
    except Exception as e:
        print(f"❌ Error en módulos de la app: {e}")
        traceback.print_exc()
        return False

def test_app_creation():
    """Prueba creación de la app"""
    try:
        print("7. Probando creación de la app...")
        
        # Agregar directorio padre al path para importar app
        import os
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, parent_dir)
        
        from app import create_app
        
        print("   - Creando app...")
        app = create_app()
        print("   ✅ App creada correctamente")
        
        print("   - Probando configuración...")
        with app.app_context():
            print(f"   ✅ App context funciona")
            print(f"   ✅ Debug mode: {app.debug}")
        
        return True
    except Exception as e:
        print(f"❌ Error en creación de la app: {e}")
        traceback.print_exc()
        return False

def main():
    print("🔍 DIAGNÓSTICO DE LA APLICACIÓN SOMYL")
    print("=" * 50)
    
    success = True
    
    success &= test_basic_imports()
    success &= test_environment()
    success &= test_app_modules()
    success &= test_app_creation()
    
    print("=" * 50)
    if success:
        print("🎉 DIAGNÓSTICO COMPLETADO: Todo funciona correctamente")
        print("   El problema puede estar en el entorno de producción")
    else:
        print("❌ DIAGNÓSTICO FALLIDO: Se encontraron errores")
        print("   Revisar los errores mostrados arriba")
    
    return success

if __name__ == "__main__":
    main()
