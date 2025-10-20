#!/bin/bash

# Script para iniciar la aplicación completa
# Uso: ./start.sh

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Obtener el directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "\n${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🚀 Iniciando Aplicación Completa 🚀              ║${NC}"
echo -e "${BLUE}║     Backend (Flask) + Frontend (React + Vite)        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n"

# Ejecutar el script Python
cd "$SCRIPT_DIR"
python nuevo_proyecto/run.py
