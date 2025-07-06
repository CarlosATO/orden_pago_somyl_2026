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
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        raise RuntimeError('Debe configurar SUPABASE_URL y SUPABASE_KEY')
    supabase = create_client(url, key)
    app.config['SUPABASE'] = supabase

    # Registrar módulos de la aplicación
    from .modules.ordenes_pago import bp as bp_op
    app.register_blueprint(bp_op, url_prefix='/ordenes_pago')
    from .modules.ordenes_pago_pdf import bp_pdf
    app.register_blueprint(bp_pdf, url_prefix='/ordenes_pago/pdf')
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

    def get_total_pendiente():
        from flask import current_app
        supabase = current_app.config["SUPABASE"]

        pagos = (
            supabase
            .table("fechas_de_pagos_op")
            .select("orden_numero")
            .execute()
            .data
        ) or []
        ids_pagados = set(int(row["orden_numero"]) for row in pagos if row.get("orden_numero") is not None)
        print("ORDENES PAGADAS:", ids_pagados)

        ordenes = (
            supabase
            .table("orden_de_pago")
            .select("orden_numero, costo_final_con_iva")
            .execute()
            .data
        ) or []
        print("ORDENES DE PAGO:", [(row.get("orden_numero"), row.get("costo_final_con_iva")) for row in ordenes])

        total = sum(
            float(row.get("costo_final_con_iva") or 0)
            for row in ordenes
            if row.get("orden_numero") is not None and int(row.get("orden_numero")) not in ids_pagados
        )
        print("TOTAL PENDIENTE:", total)
        return total

    @app.context_processor
    def inject_total_pendiente():
        try:
            total = get_total_pendiente()
        except Exception:
            total = 0
        return dict(total_pendiente=total)

    return app

bp_pagos = Blueprint('pagos', __name__)

@bp_pagos.route('/pagos/export', methods=['GET'])
def export_pagos():
    supabase = current_app.config['SUPABASE']
    response = supabase.table('pagos').select('*').execute()
    pagos = response.data

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=pagos[0].keys() if pagos else [])
    writer.writeheader()
    writer.writerows(pagos)

    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='pagos.csv'
    )