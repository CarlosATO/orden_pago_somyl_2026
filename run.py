#!/usr/bin/env python3
"""
Script wrapper para iniciar la aplicación
Ejecuta: run.py (desde cualquier lugar)
"""
import subprocess
import sys

# Ruta absoluta al script real
SCRIPT_PATH = "/Users/carlosalegria/Desktop/Migracion_OP/nuevo_proyecto/run.py"
PYTHON_PATH = "/Users/carlosalegria/Desktop/Migracion_OP/.venv/bin/python"

# Ejecutar el script con el Python del venv
sys.exit(subprocess.call([PYTHON_PATH, SCRIPT_PATH]))
