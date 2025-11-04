# backend/app.py

# backend/app.py
import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client

# Cargar variables de entorno desde el archivo .env
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # --- Configuración de CORS ---
    CORS(app, resources={r"/*": {"origins": "*"}})

    # --- Configuración General ---
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")

    # --- Configuración de Supabase ---
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    app.config['SUPABASE'] = create_client(url, key)

    # --- Registrar Blueprints (módulos de la API) ---

    from .modules.auth import bp as auth_bp
    from .modules.ordenes import bp as ordenes_bp
    from .modules.ordenes_pago import bp as ordenes_pago_bp
    from .modules.ingresos import bp as ingresos_bp
    from .modules.proveedores import bp as proveedores_bp
    from .modules.presupuestos import bp as presupuestos_bp
    from .modules.pagos import bp as pagos_api_bp
    from .modules.documentos_pendientes import bp as bp_documentos_pendientes
    from .modules.estado_presupuesto import bp as estado_presupuesto_bp
    from .modules.proyectos import bp as proyectos_bp
    from .modules.materiales import bp as materiales_bp
    from .modules.items import bp as items_bp
    from .modules.trabajadores import bp as trabajadores_bp
    from .modules.usuarios import bp as usuarios_bp
    from .rutas.pdf_orden_compra_routes import pdf_oc_bp
    from .rutas.graficos_presupuesto_routes import bp as graficos_presupuesto_bp
    from .modules.gastos_directos import bp as gastos_directos_bp
    from .modules.ordenes_no_recepcionadas import bp as ordenes_no_recepcionadas_bp
    from .modules.dashboard import bp as dashboard_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(pagos_api_bp, url_prefix='/api/pagos')
    app.register_blueprint(bp_documentos_pendientes, url_prefix='/api/documentos-pendientes')
    app.register_blueprint(estado_presupuesto_bp, url_prefix='/api/estado-presupuesto')
    app.register_blueprint(ordenes_bp, url_prefix='/api/ordenes')
    app.register_blueprint(ordenes_pago_bp, url_prefix='/api/ordenes_pago')
    app.register_blueprint(ingresos_bp, url_prefix='/api/ingresos')
    app.register_blueprint(proveedores_bp, url_prefix='/api/proveedores')
    app.register_blueprint(presupuestos_bp, url_prefix='/api/presupuestos')
    app.register_blueprint(proyectos_bp, url_prefix='/api/proyectos')
    app.register_blueprint(materiales_bp, url_prefix='/api/materiales')
    app.register_blueprint(items_bp, url_prefix='/api/items')
    app.register_blueprint(trabajadores_bp, url_prefix='/api/trabajadores')
    app.register_blueprint(usuarios_bp, url_prefix='/api/usuarios')
    app.register_blueprint(gastos_directos_bp, url_prefix='/api/gastos_directos')
    app.register_blueprint(ordenes_no_recepcionadas_bp, url_prefix='/api/ordenes-no-recepcionadas')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(pdf_oc_bp, url_prefix='/api')
    app.register_blueprint(graficos_presupuesto_bp, url_prefix='/api')

    # --- Ruta de prueba ---
    @app.route('/api/health')
    def health_check():
        return jsonify({"status": "ok", "message": "API funcionando!"})

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)
