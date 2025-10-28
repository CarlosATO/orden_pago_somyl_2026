#!/usr/bin/env python3
"""Script para probar los endpoints del módulo Presupuestos"""

import requests
import json

BASE_URL = "http://localhost:5001"

def test_login():
    """Probar login y obtener token"""
    print("=" * 60)
    print("1. Probando LOGIN")
    print("=" * 60)
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "correo": "carlosalegria@me.com",
            "password": "camilo"
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        return response.json().get("token")
    return None

def test_proyectos(token):
    """Probar endpoint de proyectos"""
    print("\n" + "=" * 60)
    print("2. Probando GET /api/proyectos")
    print("=" * 60)
    
    response = requests.get(
        f"{BASE_URL}/api/proyectos",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()

def test_items(token):
    """Probar endpoint de items"""
    print("\n" + "=" * 60)
    print("3. Probando GET /api/items")
    print("=" * 60)
    
    response = requests.get(
        f"{BASE_URL}/api/items",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()

if __name__ == "__main__":
    print("\n🧪 PRUEBA DE ENDPOINTS - MÓDULO PRESUPUESTOS\n")
    
    # 1. Login
    token = test_login()
    
    if not token:
        print("\n❌ Error: No se pudo obtener el token")
        exit(1)
    
    print(f"\n✅ Token obtenido: {token[:30]}...")
    
    # 2. Proyectos
    test_proyectos(token)
    
    # 3. Items
    test_items(token)
    
    print("\n" + "=" * 60)
    print("✅ PRUEBAS COMPLETADAS")
    print("=" * 60 + "\n")
