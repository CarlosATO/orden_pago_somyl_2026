# inicio app.py 
# -*- coding: utf-8 -*-
import os
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, request, redirect
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client
import jwt
from werkzeug.middleware.proxy_fix import ProxyFix 

# Cargar variables de entorno
load_dotenv()

def create_app():
    # Configuración de carpeta estática
    static_dir = Path(__file__).parent / 'frontend_dist'
    if static_dir.exists():
        app = Flask(__name__, static_folder=str(static_dir), static_url_path='')
        app.logger.info(f"Static folder set to: {app.static_folder}")
        index_file = Path(app.static_folder) / 'index.html'
        app.logger.info(f"Index file exists: {index_file.exists()}")
    else:
        app = Flask(__name__)
        app.logger.info("Static dir does not exist, no static folder set")
    
    # Configuración para HTTPS en Railway
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    CORS(app, resources={r"/*": {"origins": "*"}})
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")

    # Supabase (crear cliente solo si están las variables)
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    if url and key:
        try:
            app.config['SUPABASE'] = create_client(url, key)
        except Exception as e:
            app.logger.warning(f"No se pudo inicializar Supabase client: {e}")
            app.config['SUPABASE'] = None
    else:
        app.logger.warning("Variables SUPABASE_URL/SUPABASE_KEY no definidas; continuando sin cliente Supabase")
        app.config['SUPABASE'] = None

    # --- Imports de Módulos ---
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
    from .modules.chatbot import bp as chatbot_bp

    # --- Registro de Blueprints ---
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
    app.register_blueprint(chatbot_bp, url_prefix='/api/chatbot')

    # ==========================================
    # ZONA SSO
    # ==========================================
    @app.route('/sso/login', methods=['GET'])
    def sso_receiver():
        token = request.args.get('token')
        if not token:
            return jsonify({'error': 'Token SSO no recibido'}), 400

        email = ''
        referrer = request.referrer or 'https://portal.datix.cl'  # Default al portal
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            email = payload.get('email', '')
        except:
            pass

        # Redirigir a la app principal pasando el token y referrer
        return redirect(f"/?sso_token={token}&sso_user={email}&referrer={referrer}")

    @app.route('/api/health')
    def health_check():
        return jsonify({"status": "ok", "message": "API funcionando!"})

    # Serve frontend
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        app.logger.info(f"Serving frontend for path: {path}")
        if path.startswith('api/') or path.startswith('auth/'):
            return jsonify({"message": "Recurso no encontrado"}), 404
        
        if app.static_folder:
            static_path = Path(app.static_folder)
            app.logger.info(f"Static folder: {app.static_folder}")
            if path and (static_path / path).exists() and not path.startswith('api') and not path.startswith('auth'):
                return send_from_directory(app.static_folder, path)
            
            index_file = static_path / 'index.html'
            app.logger.info(f"Index file: {index_file}, exists: {index_file.exists()}")
            if index_file.exists():
                return send_from_directory(app.static_folder, 'index.html')
        
        # Si no hay frontend (o no se encontró el index), devolvemos 200 para
        # que los healthchecks del proveedor consideren la app UP. El endpoint
        # real de estado está en /api/health. Esto evita fallos cuando el build
        # del frontend no produce `frontend_dist` o durante despliegues.
        return jsonify({"status": "ok", "message": "backend running (frontend not found)"}), 200

    return app

# Exponemos la app GLOBALMENTE
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
