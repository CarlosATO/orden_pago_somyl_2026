#!/usr/bin/env python3
"""
Script de verificación pre-deployment
Verifica que todos los archivos estén listos para Railway
"""

import os
from pathlib import Path

# Colores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_file_exists(file_path, description):
    """Verifica que un archivo existe"""
    if Path(file_path).exists():
        print(f"{GREEN}✓{RESET} {description}: {file_path}")
        return True
    else:
        print(f"{RED}✗{RESET} {description}: {file_path} - FALTANTE")
        return False

def check_imports_consistency():
    """Verifica que los imports coincidan con nombres de archivos"""
    app_jsx = Path("nuevo_proyecto/frontend/src/App.jsx")
    components_dir = Path("nuevo_proyecto/frontend/src/components")
    
    if not app_jsx.exists():
        print(f"{RED}✗{RESET} App.jsx no encontrado")
        return False
    
    with open(app_jsx, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar imports críticos
    imports_to_check = [
        ("GastosDirectos", "GastosDirectos.jsx"),
        ("OrdenesPago", "OrdenesPago.jsx"),
        ("OrdenesNoRecepcionadas", "OrdenesNoRecepcionadas.jsx"),
    ]
    
    all_ok = True
    for import_name, file_name in imports_to_check:
        file_path = components_dir / file_name
        if file_path.exists():
            if f"from './components/{import_name}'" in content:
                print(f"{GREEN}✓{RESET} Import de {import_name} correcto")
            else:
                print(f"{YELLOW}⚠{RESET} Import de {import_name} no encontrado en App.jsx")
                all_ok = False
        else:
            print(f"{RED}✗{RESET} Archivo {file_name} no existe")
            all_ok = False
    
    return all_ok

def check_dockerfile():
    """Verifica la configuración del Dockerfile"""
    dockerfile = Path("Dockerfile")
    
    if not dockerfile.exists():
        print(f"{RED}✗{RESET} Dockerfile no encontrado")
        return False
    
    with open(dockerfile, 'r') as f:
        content = f.read()
    
    # Verificar versión de Node
    if "FROM node:20-alpine" in content:
        print(f"{GREEN}✓{RESET} Dockerfile usa Node 20")
    else:
        print(f"{RED}✗{RESET} Dockerfile no usa Node 20")
        return False
    
    # Verificar que se copie el frontend build
    if "COPY --from=frontend-builder /app/frontend/dist ./backend/frontend_dist" in content:
        print(f"{GREEN}✓{RESET} Dockerfile copia frontend_dist correctamente")
    else:
        print(f"{RED}✗{RESET} Dockerfile no copia frontend_dist")
        return False
    
    return True

def main():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}  Verificación Pre-Deployment para Railway{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    checks_passed = 0
    total_checks = 0
    
    # 1. Verificar archivos críticos
    print(f"\n{BLUE}1. Verificando archivos críticos...{RESET}")
    files_to_check = [
        ("Dockerfile", "Dockerfile de multi-stage"),
        ("start.sh", "Script de inicio"),
        (".dockerignore", "Archivo dockerignore"),
        ("nuevo_proyecto/backend/app.py", "Aplicación Flask"),
        ("nuevo_proyecto/backend/requirements.txt", "Dependencias Python"),
        ("nuevo_proyecto/frontend/package.json", "Configuración Node"),
        ("nuevo_proyecto/frontend/src/App.jsx", "App principal React"),
    ]
    
    for file_path, desc in files_to_check:
        total_checks += 1
        if check_file_exists(file_path, desc):
            checks_passed += 1
    
    # 2. Verificar imports
    print(f"\n{BLUE}2. Verificando consistencia de imports...{RESET}")
    total_checks += 1
    if check_imports_consistency():
        checks_passed += 1
        print(f"{GREEN}✓{RESET} Imports consistentes")
    
    # 3. Verificar Dockerfile
    print(f"\n{BLUE}3. Verificando Dockerfile...{RESET}")
    total_checks += 1
    if check_dockerfile():
        checks_passed += 1
    
    # 4. Verificar componentes renombrados
    print(f"\n{BLUE}4. Verificando componentes renombrados...{RESET}")
    components_to_check = [
        ("nuevo_proyecto/frontend/src/components/GastosDirectos.jsx", "GastosDirectos"),
        ("nuevo_proyecto/frontend/src/components/GastosDirectos.css", "GastosDirectos CSS"),
        ("nuevo_proyecto/frontend/src/components/OrdenesPago.jsx", "OrdenesPago"),
        ("nuevo_proyecto/frontend/src/components/OrdenesPago.css", "OrdenesPago CSS"),
        ("nuevo_proyecto/frontend/src/components/OrdenesNoRecepcionadas.jsx", "OrdenesNoRecepcionadas"),
        ("nuevo_proyecto/frontend/src/components/OrdenesNoRecepcionadas.css", "OrdenesNoRecepcionadas CSS"),
    ]
    
    for file_path, desc in components_to_check:
        total_checks += 1
        if check_file_exists(file_path, desc):
            checks_passed += 1
    
    # Resumen
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"\n{BLUE}Resumen:{RESET}")
    print(f"Checks pasados: {checks_passed}/{total_checks}")
    
    if checks_passed == total_checks:
        print(f"\n{GREEN}✓ ¡Todo listo para deployment en Railway!{RESET}\n")
        print(f"{BLUE}Próximos pasos:{RESET}")
        print(f"  1. git add .")
        print(f"  2. git commit -m 'Fix: Corregir imports y actualizar a Node 20 para Railway'")
        print(f"  3. git push")
        print(f"  4. Railway hará auto-deploy\n")
        return 0
    else:
        print(f"\n{RED}✗ Hay {total_checks - checks_passed} problema(s) que resolver{RESET}\n")
        return 1

if __name__ == "__main__":
    exit(main())
