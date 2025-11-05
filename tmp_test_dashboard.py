import traceback, sys
from nuevo_proyecto.backend.modules import dashboard

print('Llamando a obtener_dashboard_completo()...')
try:
    data = dashboard.obtener_dashboard_completo()
    print('Resultado tipo:', type(data))
    print('Claves devueltas:', list(data.keys()) if isinstance(data, dict) else 'N/A')
except Exception:
    traceback.print_exc()
    sys.exit(1)
