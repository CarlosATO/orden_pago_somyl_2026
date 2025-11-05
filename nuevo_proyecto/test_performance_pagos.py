#!/usr/bin/env python3
"""
Script para probar el rendimiento del módulo de pagos con caché.
"""

import requests
import time
import json

# Configuración
BASE_URL = "http://localhost:5001/api/pagos"
TOKEN = None  # Se obtendrá del login

def login():
    """Obtener token de autenticación"""
    global TOKEN
    response = requests.post(
        "http://localhost:5001/api/auth/login",
        json={
            "email": "admin@admin.com",  # Ajustar según tu usuario
            "password": "admin"
        }
    )
    if response.status_code == 200:
        data = response.json()
        TOKEN = data.get("data", {}).get("token")
        print(f"✓ Login exitoso. Token obtenido.")
        return True
    else:
        print(f"✗ Error en login: {response.status_code}")
        print(response.text)
        return False

def test_performance(estado=None, descripcion=""):
    """Prueba el rendimiento de list_pagos"""
    if not TOKEN:
        print("Error: No hay token. Ejecuta login() primero.")
        return
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {"page": 1, "per_page": 50}
    
    if estado:
        params["estado"] = estado
    
    print(f"\n{'='*60}")
    print(f"Prueba: {descripcion}")
    print(f"Parámetros: {params}")
    print(f"{'='*60}")
    
    start = time.time()
    response = requests.get(BASE_URL, headers=headers, params=params)
    elapsed = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        total = data.get("data", {}).get("pagination", {}).get("total", 0)
        print(f"✓ Respuesta exitosa")
        print(f"  Total registros: {total}")
        print(f"  Tiempo: {elapsed:.3f} segundos")
        
        # Clasificar el rendimiento
        if elapsed < 0.5:
            print(f"  Rendimiento: ⚡ EXCELENTE (< 0.5s)")
        elif elapsed < 2:
            print(f"  Rendimiento: ✓ BUENO (< 2s)")
        elif elapsed < 5:
            print(f"  Rendimiento: ⚠ ACEPTABLE (< 5s)")
        else:
            print(f"  Rendimiento: ✗ LENTO (> 5s)")
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)

def main():
    print("\n" + "="*60)
    print("PRUEBA DE RENDIMIENTO - MÓDULO DE PAGOS CON CACHÉ")
    print("="*60)
    
    # 1. Login
    if not login():
        return
    
    # 2. Primera carga sin filtro (normal, debe ser rápido)
    test_performance(
        estado=None,
        descripcion="Sin filtro de estado (paginación normal)"
    )
    
    # 3. Primera carga con filtro "pendiente" (cache miss, puede ser lento)
    test_performance(
        estado="pendiente",
        descripcion="PRIMERA carga con filtro 'pendiente' (CACHE MISS)"
    )
    
    # 4. Segunda carga con filtro "pendiente" (cache hit, debe ser rápido)
    time.sleep(1)  # Pequeña pausa
    test_performance(
        estado="pendiente",
        descripcion="SEGUNDA carga con filtro 'pendiente' (CACHE HIT esperado)"
    )
    
    # 5. Filtro "abono" (cache hit, debe ser rápido)
    test_performance(
        estado="abono",
        descripcion="Filtro 'abono' (CACHE HIT esperado)"
    )
    
    # 6. Filtro "pagado" (cache hit, debe ser rápido)
    test_performance(
        estado="pagado",
        descripcion="Filtro 'pagado' (CACHE HIT esperado)"
    )
    
    print("\n" + "="*60)
    print("RESUMEN:")
    print("- Primera carga con filtro: Esperado 2-3s (cache miss)")
    print("- Cargas subsecuentes: Esperado < 0.5s (cache hit)")
    print("- Sin filtro: Esperado < 1s (paginación normal)")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
