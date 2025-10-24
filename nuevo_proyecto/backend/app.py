# backend/app.py

# backend/app.py
import os
from flask import Flask, jsonify
from dotenv import load_dotenv
from supabase import create_client

# Cargar variables de entorno desde el archivo .env
load_dotenv()

def create_app():
    app = Flask(__name__)

    # --- Configuración General ---
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")

    # --- Configuración de Supabase ---
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    app.config['SUPABASE'] = create_client(url, key)

    # --- Registrar Blueprints (módulos de la API) ---
    from .modules.auth import bp as auth_bp
    from .modules.ordenes import bp as ordenes_bp
    from .modules.ingresos import bp as ingresos_bp
    from .modules.proveedores import bp as proveedores_bp
    from .rutas.pdf_orden_compra_routes import pdf_oc_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(ordenes_bp, url_prefix='/api/ordenes')
    app.register_blueprint(ingresos_bp, url_prefix='/api/ingresos')
    app.register_blueprint(proveedores_bp, url_prefix='/api/proveedores')
    app.register_blueprint(pdf_oc_bp, url_prefix='/api')

    # --- Ruta de prueba ---
    @app.route('/api/health')
    def health_check():
        return jsonify({"status": "ok", "message": "API funcionando!"})

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)
