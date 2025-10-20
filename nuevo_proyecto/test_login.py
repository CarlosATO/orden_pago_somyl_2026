#!/usr/bin/env python3
"""
Script de prueba para verificar el login
"""
import requests
import json

# Configuración
BACKEND_URL = "http://localhost:5001"
TEST_USER = {
    "email": "carlosalegria@me.com",
    "password": "camilo"
}

def test_health():
    """Prueba el health check del backend"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/health")
        print(f"✅ Health Check: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Error en health check: {e}")
        return False

def test_login():
    """Prueba el endpoint de login"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/login",
            json=TEST_USER,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n📊 Status Code: {response.status_code}")
        print(f"📄 Response:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        if response.status_code == 200:
            print("\n✅ LOGIN EXITOSO!")
            return True
        else:
            print("\n❌ LOGIN FALLÓ")
            return False
            
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Iniciando pruebas del backend...\n")
    print("="*60)
    
    # Prueba 1: Health Check
    print("\n1️⃣ Probando Health Check...")
    if not test_health():
        print("❌ Backend no está disponible")
        exit(1)
    
    # Prueba 2: Login
    print("\n2️⃣ Probando Login...")
    print(f"   Usuario: {TEST_USER['email']}")
    print(f"   Password: {'*' * len(TEST_USER['password'])}")
    
    test_login()
    
    print("\n" + "="*60)
    print("🏁 Pruebas completadas")
