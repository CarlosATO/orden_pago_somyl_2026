#!/bin/bash

# Script para restaurar el respaldo del módulo Informe de Órdenes de Pago
# Fecha del respaldo: 12 de agosto de 2025 - 14:25:29
# Uso: ./RESTAURAR.sh

echo "🔄 Iniciando restauración del módulo Informe de Órdenes de Pago..."

# Verificar que estamos en el directorio correcto
if [ ! -f "run.py" ]; then
    echo "❌ Error: Ejecutar desde el directorio raíz del proyecto"
    echo "Uso: cd /Users/carlosalegria/Desktop/Apps\ Somyl/seguimiento_ordenes && ./backup_informe_op_20250812_142529/RESTAURAR.sh"
    exit 1
fi

# Crear respaldo de los archivos actuales antes de restaurar
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "📁 Creando respaldo de archivos actuales en backup_antes_restaurar_$TIMESTAMP/"
mkdir -p backup_antes_restaurar_$TIMESTAMP
cp app/modules/informe_op.py backup_antes_restaurar_$TIMESTAMP/informe_op.py.actual
cp app/templates/informe_op.html backup_antes_restaurar_$TIMESTAMP/informe_op.html.actual

# Restaurar archivos desde el respaldo
echo "📄 Restaurando backend: app/modules/informe_op.py"
cp backup_informe_op_20250812_142529/informe_op.py.backup app/modules/informe_op.py

echo "🎨 Restaurando frontend: app/templates/informe_op.html"
cp backup_informe_op_20250812_142529/informe_op.html.backup app/templates/informe_op.html

# Verificar checksums
echo "🔐 Verificando integridad de archivos restaurados..."
echo "Backend - Líneas: $(wc -l < app/modules/informe_op.py)"
echo "Frontend - Líneas: $(wc -l < app/templates/informe_op.html)"

echo "✅ Restauración completada!"
echo "📁 Archivos anteriores guardados en: backup_antes_restaurar_$TIMESTAMP/"
echo ""
echo "🚀 Para aplicar los cambios, reinicia la aplicación Flask:"
echo "python run.py"
