#!/bin/bash
# Script para instalar wkhtmltopdf en Railway
echo "Instalando wkhtmltopdf..."

# Verificar si wkhtmltopdf está disponible
if ! command -v wkhtmltopdf &> /dev/null; then
    echo "wkhtmltopdf no encontrado, instalando..."
    
    # Para Railway (usa Nixpacks)
    if [ -f /etc/nixos/nixpkgs ]; then
        echo "Entorno Nixpacks detectado"
        # wkhtmltopdf debería estar disponible via nixpacks.toml
    else
        echo "Entorno desconocido, intentando instalación manual..."
        # Fallback para otros entornos
        apt-get update && apt-get install -y wkhtmltopdf
    fi
else
    echo "wkhtmltopdf ya está instalado en: $(which wkhtmltopdf)"
fi

# Ejecutar la aplicación
exec "$@"
