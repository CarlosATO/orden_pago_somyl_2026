

import pytest
from flask import Flask
from app.modules.pagos import bp_pagos
from flask_login import LoginManager, AnonymousUserMixin

class DummySupabase:
    def table(self, name):
        return self
    def select(self, *args, **kwargs):
        return self
    def order(self, *args, **kwargs):
        return self
    def range(self, *args, **kwargs):
        return self
    def execute(self):
        # Simula datos mínimos para la vista
        class Result:
            @property
            def data(self):
                if 'orden_de_pago' in str(self):
                    return [{
                        'orden_numero': 1,
                        'fecha': '2025-07-01',
                        'proveedor_nombre': 'Proveedor Test',
                        'detalle_compra': 'Detalle',
                        'factura': 'F123',
                        'costo_final_con_iva': 1000,
                        'proyecto': 'Proyecto X',
                        'orden_compra': 'OC1',
                        'condicion_pago': 'Contado',
                        'vencimiento': '2025-07-10',
                        'fecha_factura': '2025-07-01',
                    }]
                else:
                    return [{
                        'orden_numero': 1,
                        'fecha_pago': '2025-07-25',
                    }]
        return Result()



def app(monkeypatch):
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SUPABASE'] = DummySupabase()
    app.register_blueprint(bp_pagos)
    # Inicializa Flask-Login para rutas protegidas
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.anonymous_user = AnonymousUserMixin
    app.login_manager = login_manager  # Asegura que Flask-Login lo encuentre
    app._login_manager = login_manager  # Compatibilidad extra para Flask-Login
    # Parchea los helpers de proveedores/proyectos para evitar errores
    monkeypatch.setattr('app.utils.static_data.get_cached_proveedores', lambda: [{'nombre': 'Proveedor Test', 'cuenta': '123-456'}])
    monkeypatch.setattr('app.utils.static_data.get_cached_proyectos_with_id', lambda: [{'id': 'Proyecto X', 'proyecto': 'Proyecto X'}])
    return app
