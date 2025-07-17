#!/bin/bash
# Script de inicio para Railway Serverless
echo "Iniciando aplicación SOMYL en modo serverless..."

# Verificar si wkhtmltopdf está disponible
if command -v wkhtmltopdf &> /dev/null; then
    echo "wkhtmltopdf disponible en: $(which wkhtmltopdf)"
else
    echo "wkhtmltopdf no encontrado - usando fallback ReportLab"
fi

# Ejecutar la aplicación con configuración serverless
exec gunicorn run:app --bind 0.0.0.0:$PORT --timeout 300
