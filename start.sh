#!/bin/bash
# Script de inicio simplificado para Railway
echo "Iniciando aplicación SOMYL..."

# Verificar si wkhtmltopdf está disponible
if command -v wkhtmltopdf &> /dev/null; then
    echo "wkhtmltopdf disponible en: $(which wkhtmltopdf)"
else
    echo "wkhtmltopdf no encontrado - usando fallback ReportLab"
fi

# Ejecutar la aplicación
exec gunicorn run:app --bind 0.0.0.0:$PORT --workers 4 --timeout 300
