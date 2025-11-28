#!/bin/bash

# Script para corregir el alias de run.py
# Ejecutar: bash fix_alias.sh

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "\n${BLUE}🔧 Corrigiendo alias de run.py...${NC}\n"

ZSHRC="$HOME/.zshrc"
OLD_ALIAS="alias run.py='/Users/carlosalegria/Desktop/Nuevo\ proyecto\ OP/run.py'"
NEW_ALIAS="alias run.py='python /Users/carlosalegria/Desktop/Migracion_OP/run.py'"

# Hacer backup del .zshrc
cp "$ZSHRC" "$ZSHRC.backup.$(date +%Y%m%d_%H%M%S)"
echo -e "${GREEN}✅ Backup creado: $ZSHRC.backup.$(date +%Y%m%d_%H%M%S)${NC}"

# Eliminar alias viejos que contengan "run.py"
sed -i.tmp '/alias run\.py=/d' "$ZSHRC"
sed -i.tmp '/Alias para proyecto Migracion_OP/d' "$ZSHRC"
rm -f "$ZSHRC.tmp"

# Agregar el nuevo alias
echo "" >> "$ZSHRC"
echo "# Alias para proyecto Migracion_OP - Actualizado $(date)" >> "$ZSHRC"
echo "$NEW_ALIAS" >> "$ZSHRC"

echo -e "${GREEN}✅ Alias corregido en ~/.zshrc${NC}\n"

echo -e "${YELLOW}Para activar en esta sesión, ejecuta:${NC}"
echo -e "${BLUE}source ~/.zshrc${NC}\n"

echo -e "${GREEN}Después podrás usar simplemente:${NC}"
echo -e "${BLUE}run.py${NC}\n"
