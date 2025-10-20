#!/bin/bash

# Script para configurar alias en zsh
# Ejecutar: bash setup_alias.sh

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "\n${BLUE}🔧 Configurando alias para run.py...${NC}\n"

ZSHRC="$HOME/.zshrc"
ALIAS_LINE='alias run.py="python /Users/carlosalegria/Desktop/Migracion_OP/run.py"'

# Verificar si el alias ya existe
if grep -q "alias run.py=" "$ZSHRC" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  El alias 'run.py' ya existe en .zshrc${NC}"
else
    # Agregar el alias al .zshrc
    echo "" >> "$ZSHRC"
    echo "# Alias para proyecto Migracion_OP" >> "$ZSHRC"
    echo "$ALIAS_LINE" >> "$ZSHRC"
    echo -e "${GREEN}✅ Alias agregado a ~/.zshrc${NC}"
fi

echo -e "\n${BLUE}Para activar el alias en la sesión actual, ejecuta:${NC}"
echo -e "${YELLOW}source ~/.zshrc${NC}\n"

echo -e "${BLUE}Después podrás ejecutar desde cualquier lugar:${NC}"
echo -e "${GREEN}run.py${NC}\n"
