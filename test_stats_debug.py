import requests
import json

# URL del endpoint
url = "http://localhost:5001/api/pagos/stats?debug=1"

# Token de autenticación (usa uno válido)
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJub21icmUiOiJDQVJMT1MgQUxFR1JJQSIsImV4cCI6MTc2MjM5MTk3Nn0.wgk8nkRkbWHIdi0fB8XSLD-Iv0cnLOepQk-NqdFdgTU"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print("\nRespuesta:")
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    if data.get("success") and "debug" in data.get("data", {}):
        debug = data["data"]["debug"]
        print("\n" + "="*60)
        print("ANÁLISIS DE DEBUG:")
        print("="*60)
        print(f"Filas consultadas: {debug.get('filas_consultadas')}")
        print(f"Órdenes únicas: {debug.get('ordenes_unicas_consideradas')}")
        print(f"Órdenes con fecha: {debug.get('ordenes_con_fecha_count')}")
        print(f"Órdenes con abonos: {debug.get('ordenes_con_abonos_count')}")
        print("\nMuestra de 20 órdenes:")
        print(f"Órdenes: {debug.get('muestra_ordenes')}")
        print(f"Fechas: {debug.get('muestra_fechas')}")
        print(f"Abonos: {debug.get('muestra_abonos')}")
        
        print("\n" + "="*60)
        print("ESTADÍSTICAS FINALES:")
        print("="*60)
        print(f"Total órdenes: {data['data'].get('total_ordenes')}")
        print(f"Pagadas: {data['data'].get('pagadas')}")
        print(f"Pendientes: {data['data'].get('pendientes')}")
        print(f"Con Abonos: {data['data'].get('con_abonos')}")
        print(f"Monto pendiente: ${data['data'].get('monto_pendiente'):,.0f}")
        print(f"Saldo abonos: ${data['data'].get('saldo_abonos'):,.0f}")
        print(f"Total general: ${data['data'].get('total_general'):,.0f}")
        
        if "ordenes_con_abonos_detalle" in debug:
            print("\n" + "="*60)
            print("DETALLE DE ÓRDENES CON ABONOS:")
            print("="*60)
            detalle = debug.get('ordenes_con_abonos_detalle', [])
            print(f"Total órdenes con abonos: {len(detalle)}")
            print(f"\n{'Orden':<10} {'Total':<15} {'Abonado':<15} {'Saldo':<15} {'Proyecto'}")
            print("="*80)
            for item in detalle:
                print(f"{item['orden']:<10} ${item['total']:>12,} ${item['abonado']:>12,} ${item['saldo']:>12,} {item['proyecto']}")
            print("="*80)
        
except Exception as e:
    print(f"Error: {e}")
