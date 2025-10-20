#!/usr/bin/env python
# Script para ejecutar el backend
import sys
import os

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

from backend.app import create_app

if __name__ == '__main__':
    app = create_app()
    print("\n" + "="*50)
    print("🚀 Backend iniciado en: http://localhost:5001")
    print("📋 Health check: http://localhost:5001/api/health")
    print("="*50 + "\n")
    app.run(debug=True, port=5001, host='0.0.0.0')
