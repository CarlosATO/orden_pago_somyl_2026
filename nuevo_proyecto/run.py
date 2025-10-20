#!/usr/bin/env python3
"""
Script para iniciar Backend (Flask) y Frontend (Vite) simultáneamente
Ejecutar desde cualquier ubicación: python run.py
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

# Colores para la terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Obtener el directorio del script (donde está run.py)
SCRIPT_DIR = Path(__file__).parent.absolute()
BACKEND_DIR = SCRIPT_DIR / "backend"
FRONTEND_DIR = SCRIPT_DIR / "frontend"
# Buscar el venv en la carpeta Migracion_OP
PROJECT_ROOT = SCRIPT_DIR.parent  # /Users/carlosalegria/Desktop/Migracion_OP
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"

# Procesos para manejar
processes = []

def signal_handler(sig, frame):
    """Maneja la señal de interrupción (Ctrl+C)"""
    print(f"\n\n{Colors.WARNING}🛑 Deteniendo servidores...{Colors.ENDC}")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    print(f"{Colors.OKGREEN}✅ Servidores detenidos correctamente{Colors.ENDC}")
    sys.exit(0)

def check_dependencies():
    """Verifica que las dependencias estén instaladas"""
    print(f"\n{Colors.OKCYAN}🔍 Verificando dependencias...{Colors.ENDC}")
    
    # Verificar Python venv
    if not VENV_PYTHON.exists():
        print(f"{Colors.FAIL}❌ No se encontró el entorno virtual de Python{Colors.ENDC}")
        print(f"   Ruta esperada: {VENV_PYTHON}")
        return False
    
    # Verificar node_modules en frontend
    if not (FRONTEND_DIR / "node_modules").exists():
        print(f"{Colors.WARNING}⚠️  Instalando dependencias de Node.js...{Colors.ENDC}")
        try:
            subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)
            print(f"{Colors.OKGREEN}✅ Dependencias de Node.js instaladas{Colors.ENDC}")
        except subprocess.CalledProcessError:
            print(f"{Colors.FAIL}❌ Error instalando dependencias de Node.js{Colors.ENDC}")
            return False
    
    print(f"{Colors.OKGREEN}✅ Todas las dependencias están listas{Colors.ENDC}")
    return True

def start_backend():
    """Inicia el servidor Flask del backend"""
    print(f"\n{Colors.OKBLUE}🚀 Iniciando Backend (Flask)...{Colors.ENDC}")
    
    # Crear el script run_backend.py si no existe
    run_backend_script = SCRIPT_DIR / "run_backend.py"
    
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'  # Para ver la salida en tiempo real
    
    try:
        proc = subprocess.Popen(
            [str(VENV_PYTHON), str(run_backend_script)],
            cwd=SCRIPT_DIR,
            env=env,
            # Redirigir stdout y stderr para que se muestren en la terminal
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        processes.append(proc)
        
        # Esperar a que el backend esté listo
        print(f"{Colors.OKCYAN}   Esperando que el backend esté listo...{Colors.ENDC}")
        time.sleep(3)
        
        if proc.poll() is None:
            print(f"{Colors.OKGREEN}   ✅ Backend iniciado en http://localhost:5001{Colors.ENDC}")
            return True
        else:
            # El proceso terminó, obtener el error
            stdout, stderr = proc.communicate(timeout=1)
            print(f"{Colors.FAIL}   ❌ El backend falló al iniciar{Colors.ENDC}")
            if stdout:
                print(f"{Colors.FAIL}   STDOUT: {stdout}{Colors.ENDC}")
            if stderr:
                print(f"{Colors.FAIL}   STDERR: {stderr}{Colors.ENDC}")
            return False
            print(f"{Colors.FAIL}   ❌ El backend falló al iniciar{Colors.ENDC}")
            return False
            
    except Exception as e:
        print(f"{Colors.FAIL}   ❌ Error al iniciar backend: {e}{Colors.ENDC}")
        return False

def start_frontend():
    """Inicia el servidor Vite del frontend"""
    print(f"\n{Colors.OKBLUE}🚀 Iniciando Frontend (Vite)...{Colors.ENDC}")
    
    try:
        proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=FRONTEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(proc)
        
        # Esperar a que el frontend esté listo
        print(f"{Colors.OKCYAN}   Esperando que el frontend esté listo...{Colors.ENDC}")
        time.sleep(3)
        
        if proc.poll() is None:
            print(f"{Colors.OKGREEN}   ✅ Frontend iniciado en http://localhost:5173{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.FAIL}   ❌ El frontend falló al iniciar{Colors.ENDC}")
            return False
            
    except Exception as e:
        print(f"{Colors.FAIL}   ❌ Error al iniciar frontend: {e}{Colors.ENDC}")
        return False

def monitor_processes():
    """Monitorea los procesos y muestra su salida"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}{Colors.BOLD}✨ ¡Aplicación iniciada exitosamente! ✨{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"\n{Colors.OKCYAN}📱 Frontend:{Colors.ENDC} {Colors.BOLD}http://localhost:5173{Colors.ENDC}")
    print(f"{Colors.OKCYAN}🔧 Backend API:{Colors.ENDC} {Colors.BOLD}http://localhost:5001{Colors.ENDC}")
    print(f"{Colors.OKCYAN}🏥 Health Check:{Colors.ENDC} {Colors.BOLD}http://localhost:5001/api/health{Colors.ENDC}")
    print(f"\n{Colors.WARNING}Presiona Ctrl+C para detener todos los servidores{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
    
    try:
        # Mantener el script corriendo
        while True:
            time.sleep(1)
            # Verificar si algún proceso ha terminado
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    name = "Backend" if i == 0 else "Frontend"
                    print(f"\n{Colors.FAIL}❌ {name} se ha detenido inesperadamente{Colors.ENDC}")
                    signal_handler(None, None)
    except KeyboardInterrupt:
        signal_handler(None, None)

def main():
    """Función principal"""
    # Registrar el manejador de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("╔════════════════════════════════════════════════════════╗")
    print("║     🚀 Iniciando Aplicación Completa 🚀              ║")
    print("║     Backend (Flask) + Frontend (React + Vite)        ║")
    print("╚════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")
    
    # Verificar dependencias
    if not check_dependencies():
        print(f"\n{Colors.FAIL}❌ No se pudo iniciar la aplicación{Colors.ENDC}")
        sys.exit(1)
    
    # Iniciar backend
    if not start_backend():
        print(f"\n{Colors.FAIL}❌ No se pudo iniciar el backend{Colors.ENDC}")
        sys.exit(1)
    
    # Iniciar frontend
    if not start_frontend():
        print(f"\n{Colors.FAIL}❌ No se pudo iniciar el frontend{Colors.ENDC}")
        signal_handler(None, None)
        sys.exit(1)
    
    # Monitorear procesos
    monitor_processes()

if __name__ == "__main__":
    main()
