#!/bin/sh

# Script para iniciar la aplicación completa (portable / POSIX)
# Uso: ./start.sh

# Colores (ANSI)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Obtener el directorio del script (compatible POSIX)
SCRIPT_DIR="$(cd "$(dirname "$0")" >/dev/null 2>&1 && pwd)"

printf "\n${BLUE}╔════════════════════════════════════════════════════════╗${NC}\n"
printf "${BLUE}║     🚀 Iniciando Aplicación Completa 🚀              ║${NC}\n"
printf "${BLUE}║     Backend (Flask) + Frontend (React + Vite)        ║${NC}\n"
printf "${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n\n"

# Ejecutar el script Python (usar python3 cuando esté disponible)
cd "$SCRIPT_DIR"
if [ "${FLASK_ENV:-development}" = "production" ]; then
	# En producción: arrancar Gunicorn para servir la app Flask
	if command -v gunicorn >/dev/null 2>&1; then
		printf "${GREEN}Iniciando Gunicorn en modo producción...${NC}\n"
		# Cambiar al directorio backend y ejecutar la aplicación con 4 workers
		cd backend
		exec gunicorn -w 4 -b 0.0.0.0:${PORT:-5001} --timeout 120 --access-logfile - --error-logfile - "app:create_app()"
	else
		printf "${RED}Error:${NC} gunicorn no está instalado en este contenedor. Instale dependencias de Python.\n"
		exit 127
	fi
else
	# Modo desarrollo (local): intentar usar python3 o python
	if command -v python3 >/dev/null 2>&1; then
		python3 nuevo_proyecto/run.py
	elif command -v python >/dev/null 2>&1; then
		# Fallback a 'python' si el contenedor lo provee
		python nuevo_proyecto/run.py
	else
		printf "${RED}Error:${NC} Python no está instalado en este contenedor. Instale python3 o use una imagen base con Python.\n"
		exit 127
	fi
fi
