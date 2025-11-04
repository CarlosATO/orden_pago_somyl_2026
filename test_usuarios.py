"""
Script de prueba para el módulo de usuarios
Verifica que todos los endpoints funcionen correctamente

Uso:
    python test_usuarios.py

Requiere:
    - Backend corriendo en http://localhost:5001
    - Token de autenticación válido
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5001"
# TODO: Reemplazar con un token válido de autenticación
TOKEN = "TU_TOKEN_AQUI"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def print_test(name, success, message=""):
    """Imprime el resultado de un test"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {name}")
    if message:
        print(f"   → {message}")
    print()

def test_get_modulos():
    """Test: Obtener lista de módulos disponibles"""
    try:
        response = requests.get(f"{BASE_URL}/api/usuarios/modulos", headers=headers)
        data = response.json()
        
        success = response.status_code == 200 and data.get("success")
        modulos = data.get("data", [])
        
        print_test(
            "GET /api/usuarios/modulos",
            success,
            f"Se encontraron {len(modulos)} módulos disponibles"
        )
        return modulos
    except Exception as e:
        print_test("GET /api/usuarios/modulos", False, str(e))
        return []

def test_get_usuarios():
    """Test: Obtener lista de usuarios"""
    try:
        response = requests.get(f"{BASE_URL}/api/usuarios/todos", headers=headers)
        data = response.json()
        
        success = response.status_code == 200 and data.get("success")
        usuarios = data.get("data", [])
        stats = data.get("stats", {})
        
        print_test(
            "GET /api/usuarios/todos",
            success,
            f"Total: {stats.get('total', 0)}, Activos: {stats.get('activos', 0)}, "
            f"Inactivos: {stats.get('inactivos', 0)}, Bloqueados: {stats.get('bloqueados', 0)}"
        )
        return usuarios
    except Exception as e:
        print_test("GET /api/usuarios/todos", False, str(e))
        return []

def test_get_usuarios_filtrado():
    """Test: Obtener usuarios filtrados por estado"""
    filtros = ['todos', 'activos', 'inactivos', 'bloqueados']
    
    for filtro in filtros:
        try:
            response = requests.get(
                f"{BASE_URL}/api/usuarios/todos?estado={filtro}",
                headers=headers
            )
            data = response.json()
            
            success = response.status_code == 200 and data.get("success")
            usuarios = data.get("data", [])
            
            print_test(
                f"GET /api/usuarios/todos?estado={filtro}",
                success,
                f"Se encontraron {len(usuarios)} usuarios con estado '{filtro}'"
            )
        except Exception as e:
            print_test(f"GET /api/usuarios/todos?estado={filtro}", False, str(e))

def test_buscar_usuarios():
    """Test: Buscar usuarios por término"""
    termino = "test"
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/usuarios/todos?buscar={termino}",
            headers=headers
        )
        data = response.json()
        
        success = response.status_code == 200 and data.get("success")
        usuarios = data.get("data", [])
        
        print_test(
            f"GET /api/usuarios/todos?buscar={termino}",
            success,
            f"Se encontraron {len(usuarios)} usuarios que coinciden con '{termino}'"
        )
    except Exception as e:
        print_test(f"GET /api/usuarios/todos?buscar={termino}", False, str(e))

def test_create_usuario(modulos):
    """Test: Crear un nuevo usuario de prueba"""
    if not modulos:
        print_test("POST /api/usuarios/new", False, "No hay módulos disponibles")
        return None
    
    # Usar solo el primer módulo
    modulo_ids = [modulos[0]['id']]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nuevo_usuario = {
        "nombre": f"Usuario Test {timestamp}",
        "email": f"test_{timestamp}@ejemplo.com",
        "password": "Test12345678",
        "activo": True,
        "modulos": modulo_ids
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/usuarios/new",
            headers=headers,
            json=nuevo_usuario
        )
        data = response.json()
        
        success = response.status_code == 200 and data.get("success")
        
        print_test(
            "POST /api/usuarios/new",
            success,
            data.get("message", "Usuario creado correctamente")
        )
        
        if success and data.get("data"):
            return data["data"]["id"]
        return None
    except Exception as e:
        print_test("POST /api/usuarios/new", False, str(e))
        return None

def test_get_usuario_by_id(usuario_id):
    """Test: Obtener un usuario por ID"""
    if not usuario_id:
        print("⏭️  Saltando test GET /api/usuarios/<id> (no hay ID)\n")
        return
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/usuarios/{usuario_id}",
            headers=headers
        )
        data = response.json()
        
        success = response.status_code == 200 and data.get("success")
        usuario = data.get("data", {})
        
        print_test(
            f"GET /api/usuarios/{usuario_id}",
            success,
            f"Usuario: {usuario.get('nombre', 'N/A')}, Email: {usuario.get('email', 'N/A')}"
        )
    except Exception as e:
        print_test(f"GET /api/usuarios/{usuario_id}", False, str(e))

def test_edit_usuario(usuario_id):
    """Test: Editar un usuario existente"""
    if not usuario_id:
        print("⏭️  Saltando test PUT /api/usuarios/edit/<id> (no hay ID)\n")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    datos_actualizados = {
        "nombre": f"Usuario Test Editado {timestamp}",
        "email": f"test_editado_{timestamp}@ejemplo.com"
    }
    
    try:
        response = requests.put(
            f"{BASE_URL}/api/usuarios/edit/{usuario_id}",
            headers=headers,
            json=datos_actualizados
        )
        data = response.json()
        
        success = response.status_code == 200 and data.get("success")
        
        print_test(
            f"PUT /api/usuarios/edit/{usuario_id}",
            success,
            data.get("message", "Usuario actualizado")
        )
    except Exception as e:
        print_test(f"PUT /api/usuarios/edit/{usuario_id}", False, str(e))

def test_toggle_estado(usuario_id):
    """Test: Cambiar estado de un usuario (activar/desactivar)"""
    if not usuario_id:
        print("⏭️  Saltando test POST /api/usuarios/toggle-estado/<id> (no hay ID)\n")
        return
    
    # Primero desactivar
    try:
        response = requests.post(
            f"{BASE_URL}/api/usuarios/toggle-estado/{usuario_id}",
            headers=headers,
            json={"activo": False}
        )
        data = response.json()
        
        success = response.status_code == 200 and data.get("success")
        
        print_test(
            f"POST /api/usuarios/toggle-estado/{usuario_id} (desactivar)",
            success,
            data.get("message", "Estado cambiado")
        )
        
        # Luego reactivar
        response = requests.post(
            f"{BASE_URL}/api/usuarios/toggle-estado/{usuario_id}",
            headers=headers,
            json={"activo": True}
        )
        data = response.json()
        
        success = response.status_code == 200 and data.get("success")
        
        print_test(
            f"POST /api/usuarios/toggle-estado/{usuario_id} (activar)",
            success,
            data.get("message", "Estado cambiado")
        )
    except Exception as e:
        print_test(f"POST /api/usuarios/toggle-estado/{usuario_id}", False, str(e))

def test_toggle_bloqueo(usuario_id):
    """Test: Bloquear/desbloquear un usuario"""
    if not usuario_id:
        print("⏭️  Saltando test POST /api/usuarios/toggle-bloqueo/<id> (no hay ID)\n")
        return
    
    # Primero bloquear
    try:
        response = requests.post(
            f"{BASE_URL}/api/usuarios/toggle-bloqueo/{usuario_id}",
            headers=headers,
            json={"bloqueado": True}
        )
        data = response.json()
        
        success = response.status_code == 200 and data.get("success")
        
        print_test(
            f"POST /api/usuarios/toggle-bloqueo/{usuario_id} (bloquear)",
            success,
            data.get("message", "Bloqueo cambiado")
        )
        
        # Luego desbloquear
        response = requests.post(
            f"{BASE_URL}/api/usuarios/toggle-bloqueo/{usuario_id}",
            headers=headers,
            json={"bloqueado": False}
        )
        data = response.json()
        
        success = response.status_code == 200 and data.get("success")
        
        print_test(
            f"POST /api/usuarios/toggle-bloqueo/{usuario_id} (desbloquear)",
            success,
            data.get("message", "Bloqueo cambiado")
        )
    except Exception as e:
        print_test(f"POST /api/usuarios/toggle-bloqueo/{usuario_id}", False, str(e))

def test_reset_password(usuario_id):
    """Test: Resetear contraseña de un usuario"""
    if not usuario_id:
        print("⏭️  Saltando test POST /api/usuarios/reset-password/<id> (no hay ID)\n")
        return
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/usuarios/reset-password/{usuario_id}",
            headers=headers
        )
        data = response.json()
        
        success = response.status_code == 200 and data.get("success")
        
        mensaje = data.get("message", "Contraseña reseteada")
        if success and data.get("password_temporal"):
            mensaje += f" (Password: {data['password_temporal'][:4]}...)"
        
        print_test(
            f"POST /api/usuarios/reset-password/{usuario_id}",
            success,
            mensaje
        )
    except Exception as e:
        print_test(f"POST /api/usuarios/reset-password/{usuario_id}", False, str(e))

def test_validaciones_create():
    """Test: Validaciones al crear usuario"""
    print("=" * 60)
    print("TESTS DE VALIDACIÓN")
    print("=" * 60)
    print()
    
    # Test 1: Email inválido
    try:
        response = requests.post(
            f"{BASE_URL}/api/usuarios/new",
            headers=headers,
            json={
                "nombre": "Test",
                "email": "email_invalido",
                "password": "12345678",
                "modulos": [1]
            }
        )
        data = response.json()
        success = response.status_code == 400 and not data.get("success")
        print_test(
            "Validación: Email inválido",
            success,
            data.get("message", "Error detectado")
        )
    except Exception as e:
        print_test("Validación: Email inválido", False, str(e))
    
    # Test 2: Password muy corta
    try:
        response = requests.post(
            f"{BASE_URL}/api/usuarios/new",
            headers=headers,
            json={
                "nombre": "Test",
                "email": "test@ejemplo.com",
                "password": "1234",
                "modulos": [1]
            }
        )
        data = response.json()
        success = response.status_code == 400 and not data.get("success")
        print_test(
            "Validación: Password muy corta",
            success,
            data.get("message", "Error detectado")
        )
    except Exception as e:
        print_test("Validación: Password muy corta", False, str(e))
    
    # Test 3: Sin módulos
    try:
        response = requests.post(
            f"{BASE_URL}/api/usuarios/new",
            headers=headers,
            json={
                "nombre": "Test",
                "email": "test@ejemplo.com",
                "password": "12345678",
                "modulos": []
            }
        )
        data = response.json()
        success = response.status_code == 400 and not data.get("success")
        print_test(
            "Validación: Sin módulos seleccionados",
            success,
            data.get("message", "Error detectado")
        )
    except Exception as e:
        print_test("Validación: Sin módulos", False, str(e))

def main():
    """Ejecuta todos los tests"""
    print("=" * 60)
    print("🧪 TESTS DEL MÓDULO DE USUARIOS")
    print("=" * 60)
    print()
    
    if TOKEN == "TU_TOKEN_AQUI":
        print("❌ ERROR: Debes configurar un token válido en la variable TOKEN")
        print("   1. Inicia sesión en el sistema")
        print("   2. Copia el token de localStorage")
        print("   3. Reemplaza 'TU_TOKEN_AQUI' en este script")
        print()
        return
    
    print(f"🔗 Base URL: {BASE_URL}")
    print(f"🔑 Token configurado: {TOKEN[:20]}...")
    print()
    
    print("=" * 60)
    print("TESTS DE LECTURA")
    print("=" * 60)
    print()
    
    # Tests de lectura
    modulos = test_get_modulos()
    usuarios = test_get_usuarios()
    test_get_usuarios_filtrado()
    test_buscar_usuarios()
    
    print("=" * 60)
    print("TESTS DE CREACIÓN Y MODIFICACIÓN")
    print("=" * 60)
    print()
    
    # Tests de escritura
    usuario_id = test_create_usuario(modulos)
    test_get_usuario_by_id(usuario_id)
    test_edit_usuario(usuario_id)
    test_toggle_estado(usuario_id)
    test_toggle_bloqueo(usuario_id)
    test_reset_password(usuario_id)
    
    # Tests de validación
    test_validaciones_create()
    
    print("=" * 60)
    print("✅ TESTS COMPLETADOS")
    print("=" * 60)
    print()
    
    if usuario_id:
        print(f"ℹ️  Se creó un usuario de prueba con ID: {usuario_id}")
        print("   Puedes eliminarlo manualmente desde la interfaz web")
        print()

if __name__ == "__main__":
    main()
