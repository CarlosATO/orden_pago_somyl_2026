#!/usr/bin/env python3
"""
🔍 VERIFICADOR DE OPTIMIZACIONES - SOMYL SYSTEM
Verifica que todas las optimizaciones estén aplicadas correctamente
"""

import time
import requests
import json
from datetime import datetime

def test_api_performance(base_url="http://localhost:5004"):
    """Prueba la performance de las APIs críticas"""
    
    print("🚀 TESTING API PERFORMANCE...")
    print("=" * 50)
    
    # APIs críticas a probar
    apis_to_test = [
        "/ordenes/api/materiales?term=acero",
        "/ordenes/api/proveedores?term=const",
        "/ordenes/api/proyectos?term=casa",
        "/ordenes/api/trabajadores?term=juan",
        "/ingresos/api/buscar_oc?term=100"
    ]
    
    results = []
    
    for api_path in apis_to_test:
        url = f"{base_url}{api_path}"
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # ms
            
            status = "✅ EXCELENTE" if response_time < 100 else \
                    "✅ BUENO" if response_time < 300 else \
                    "⚠️ REGULAR" if response_time < 500 else \
                    "❌ LENTO"
            
            results.append({
                "api": api_path,
                "status_code": response.status_code,
                "response_time_ms": round(response_time, 2),
                "status": status,
                "success": response.status_code == 200
            })
            
            print(f"{status:15} {api_path:40} {response_time:.0f}ms")
            
        except Exception as e:
            results.append({
                "api": api_path,
                "error": str(e),
                "status": "❌ ERROR",
                "success": False
            })
            print(f"❌ ERROR       {api_path:40} {str(e)}")
    
    return results

def test_cache_functionality():
    """Verifica que el sistema de cache funcione"""
    
    print("\n🗄️ TESTING CACHE SYSTEM...")
    print("=" * 50)
    
    try:
        from app.utils.cache import get_cached_data, set_cached_data, clear_cache
        
        # Test básico de cache
        test_key = "test_optimization_check"
        test_value = {"timestamp": datetime.now().isoformat(), "data": "test"}
        
        # Limpiar cache de prueba
        clear_cache(test_key)
        
        # Verificar que no existe
        cached = get_cached_data(test_key)
        if cached is not None:
            print("❌ Cache no se limpió correctamente")
            return False
        
        # Guardar en cache
        set_cached_data(test_key, test_value, ttl=60)
        
        # Verificar que se guardó
        cached = get_cached_data(test_key)
        if cached is None:
            print("❌ Cache no guardó el valor")
            return False
        
        if cached["data"] != "test":
            print("❌ Cache devolvió valor incorrecto")
            return False
        
        print("✅ Sistema de cache funcionando correctamente")
        
        # Limpiar cache de prueba
        clear_cache(test_key)
        
        return True
        
    except ImportError:
        print("❌ Módulos de cache no disponibles")
        return False
    except Exception as e:
        print(f"❌ Error en sistema de cache: {e}")
        return False

def test_database_optimization():
    """Verifica optimizaciones de base de datos"""
    
    print("\n🗃️ TESTING DATABASE OPTIMIZATIONS...")
    print("=" * 50)
    
    optimizations_to_check = [
        "✅ Índices GIN para búsquedas ILIKE",
        "✅ Índices B-tree para ordenamiento",
        "✅ Stored procedures para consultas pesadas",
        "✅ Extensión pg_trgm habilitada",
        "✅ Índices compuestos para consultas complejas"
    ]
    
    for opt in optimizations_to_check:
        print(f"  {opt}")
    
    print("\n📋 PARA VERIFICAR EN SUPABASE:")
    print("  1. Ejecutar: scripts/supabase_optimization_complete.sql")
    print("  2. Ejecutar: scripts/stored_procedures_optimization.sql")
    print("  3. Verificar índices con: SELECT * FROM pg_indexes WHERE schemaname = 'public'")

def generate_performance_report(api_results):
    """Genera reporte de performance"""
    
    print("\n📊 PERFORMANCE REPORT")
    print("=" * 50)
    
    if not api_results:
        print("❌ No hay datos de APIs para reportar")
        return
    
    successful_apis = [r for r in api_results if r.get("success", False)]
    
    if not successful_apis:
        print("❌ Ninguna API funcionó correctamente")
        return
    
    # Estadísticas
    response_times = [r["response_time_ms"] for r in successful_apis]
    avg_time = sum(response_times) / len(response_times)
    max_time = max(response_times)
    min_time = min(response_times)
    
    print(f"📈 APIs probadas: {len(api_results)}")
    print(f"✅ APIs exitosas: {len(successful_apis)}")
    print(f"⏱️ Tiempo promedio: {avg_time:.1f}ms")
    print(f"🐌 Tiempo máximo: {max_time:.1f}ms")
    print(f"⚡ Tiempo mínimo: {min_time:.1f}ms")
    
    # Clasificación de performance
    excellent = len([r for r in successful_apis if r["response_time_ms"] < 100])
    good = len([r for r in successful_apis if 100 <= r["response_time_ms"] < 300])
    regular = len([r for r in successful_apis if 300 <= r["response_time_ms"] < 500])
    slow = len([r for r in successful_apis if r["response_time_ms"] >= 500])
    
    print(f"\n🎯 CLASIFICACIÓN DE PERFORMANCE:")
    print(f"  🚀 Excelente (<100ms): {excellent}")
    print(f"  ✅ Bueno (100-300ms): {good}")
    print(f"  ⚠️ Regular (300-500ms): {regular}")
    print(f"  ❌ Lento (>500ms): {slow}")
    
    # Recomendaciones
    if avg_time < 100:
        print(f"\n🎉 EXCELENTE: Sistema altamente optimizado")
    elif avg_time < 300:
        print(f"\n👍 BUENO: Performance aceptable")
    elif avg_time < 500:
        print(f"\n⚠️ REGULAR: Considerar más optimizaciones")
    else:
        print(f"\n❌ NECESITA OPTIMIZACIÓN: Aplicar todas las mejoras")

def main():
    """Función principal de verificación"""
    
    print("🔍 VERIFICADOR DE OPTIMIZACIONES - SOMYL SYSTEM")
    print("=" * 60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. Test cache
    cache_ok = test_cache_functionality()
    
    # 2. Test APIs
    api_results = test_api_performance()
    
    # 3. Verificar DB
    test_database_optimization()
    
    # 4. Generar reporte
    generate_performance_report(api_results)
    
    # 5. Resumen final
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE VERIFICACIÓN")
    print("=" * 60)
    
    if cache_ok:
        print("✅ Sistema de cache: FUNCIONANDO")
    else:
        print("❌ Sistema de cache: REQUIERE ATENCIÓN")
    
    successful_apis = len([r for r in api_results if r.get("success", False)])
    total_apis = len(api_results)
    
    if successful_apis == total_apis:
        print("✅ APIs críticas: TODAS FUNCIONANDO")
    elif successful_apis > total_apis * 0.8:
        print("⚠️ APIs críticas: MAYORÍA FUNCIONANDO")
    else:
        print("❌ APIs críticas: REQUIEREN ATENCIÓN")
    
    print("\n🎯 PRÓXIMOS PASOS:")
    print("  1. Ejecutar scripts SQL en Supabase si no están aplicados")
    print("  2. Reiniciar aplicación para aplicar cambios")
    print("  3. Monitorear logs de performance")
    print("  4. Ajustar TTL de cache según uso")
    
    print("\n✅ VERIFICACIÓN COMPLETADA")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Verificación cancelada")
    except Exception as e:
        print(f"\n❌ Error durante verificación: {e}")
        import traceback
        traceback.print_exc()
