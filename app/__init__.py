import os
from flask import Flask
from supabase import create_client
import io
import csv
from flask import send_file, current_app, url_for
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
from flask_login import login_required, current_user

from app.modules.usuarios import get_modulos_usuario

load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configuración para evitar cache en templates
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    
    # Registrar filtro de moneda chilena
    def format_clp(value):
        try:
            v = int(value)
            s = f"{v:,}".replace(",", ".")
            return f"$ {s}"
        except Exception:
            return value
    app.jinja_env.filters['clp'] = format_clp
    app.secret_key = "S3cr3to_2025_de_Somyl"
    
    # Configurar Supabase desde variables de entorno
    url = os.getenv('SUPABASE_URL') or 'https://reubvhoexrkagmtxklek.supabase.co'
    key = os.getenv('SUPABASE_ANON_KEY') or 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJldWJ2aG9leHJrYWdtdHhrbGVrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDc3Nzc5MDUsImV4cCI6MjA2MzM1MzkwNX0.imEGNuzGcgrpyo0-Wc_1teZKft0t7RNwSJ7apoy-_sM'
    
    try:
        supabase = create_client(url, key)
        app.config['SUPABASE'] = supabase
        print(f"✅ Supabase conectado: {url[:50]}...")
    except Exception as e:
        print(f"⚠️ Error conectando Supabase: {e}")
        # En caso de error, crear un mock para que la app no falle
        app.config['SUPABASE'] = None

    # Registrar módulos de la aplicación
    from .modules.ordenes_pago import bp as bp_op
    app.register_blueprint(bp_op, url_prefix='/ordenes_pago')
    from .modules.ordenes_pago_pdf import bp_pdf
    app.register_blueprint(bp_pdf)
    
    # Registrar PDF alternativo con ReportLab
    from .modules.ordenes_pago_pdf_reportlab import bp_pdf_reportlab
    app.register_blueprint(bp_pdf_reportlab)
    
    from .modules.ordenes_pago_pendientes import bp_pending
    app.register_blueprint(bp_pending, url_prefix='/ordenes_pago/pendientes')
    from .modules.ingresos import bp as bp_ing
    app.register_blueprint(bp_ing, url_prefix='/ingresos')
    from .modules.proveedores import bp as bp_prov
    app.register_blueprint(bp_prov, url_prefix='/proveedores')
    from .modules.trabajadores import bp as bp_trab
    app.register_blueprint(bp_trab, url_prefix='/trabajadores')
    from .modules.pagos import bp_pagos
    app.register_blueprint(bp_pagos, url_prefix='/pagos')
    # Registrar módulo de materiales
    from .modules.materiales import bp as bp_mat
    app.register_blueprint(bp_mat, url_prefix='/materiales')
    from .modules.presupuestos import bp_presupuestos
    app.register_blueprint(bp_presupuestos, url_prefix='/presupuestos')

    from .modules.ordenes import bp as bp_ordenes
    app.register_blueprint(bp_ordenes, url_prefix='/ordenes')
    from .modules.proyectos import bp as bp_proyectos
    app.register_blueprint(bp_proyectos, url_prefix='/proyectos')

    # Registrar módulo de estado de presupuesto
    from .modules.estado_presupuesto import bp_estado_presupuesto
    app.register_blueprint(bp_estado_presupuesto, url_prefix='/estado_presupuesto')

    # Registrar módulo de usuarios
    from .modules.usuarios import bp as bp_usuarios
    app.register_blueprint(bp_usuarios, url_prefix='/usuarios')

    # Registrar módulo de gastos directos
    from .modules.gastos_directos import bp_gastos_directos
    app.register_blueprint(bp_gastos_directos)

    # Registrar módulo de items
    from .modules.items import bp as bp_items
    app.register_blueprint(bp_items, url_prefix='/items')

    # Ruta raíz: redirige al listado de órdenes de pago
    @app.route('/')
    @login_required
    def index():
        from flask import redirect, url_for
        return redirect(url_for('ordenes_pago.list_ordenes_pago'))

    from app.modules.auth import bp_auth, login_manager
    app.register_blueprint(bp_auth)
    login_manager.init_app(app)

    @app.context_processor
    def inject_modulos_usuario():
        if current_user.is_authenticated:
            return {'modulos_usuario': get_modulos_usuario()}
        return {'modulos_usuario': []}

    from app.utils.pendiente_global import get_total_pendiente_global

    @app.context_processor
    def inject_total_pendiente():
        try:
            total = get_total_pendiente_global()
        except Exception:
            total = 0
        return dict(total_pendiente=total)

    # Agregar headers para evitar cache
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return app
