#!/bin/bash

echo "🔄 Reiniciando backend..."

# Matar procesos anteriores
pkill -f "python.*run.py" 2>/dev/null
pkill -f "python.*app.py" 2>/dev/null

echo "⏳ Esperando 2 segundos..."
sleep 2

# Activar entorno virtual y arrancar
cd /Users/carlosalegria/Desktop/Migracion_OP/nuevo_proyecto
source /Users/carlosalegria/Desktop/Migracion_OP/.venv/bin/activate

echo "🚀 Iniciando backend en puerto 5001..."
python run.py

echo "✅ Backend reiniciado"
