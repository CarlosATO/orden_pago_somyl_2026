import requests
import json

# URL del endpoint
url = "http://localhost:5001/api/pagos?estado=abono&per_page=100"

# Token de autenticación
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJub21icmUiOiJDQVJMT1MgQUxFR1JJQSIsImV4cCI6MTc2MjM5MTk3Nn0.wgk8nkRkbWHIdi0fB8XSLD-Iv0cnLOepQk-NqdFdgTU"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            pagos = data["data"]["pagos"]
            print(f"\n📊 Total de órdenes CON ABONOS: {len(pagos)}")
            print("\n" + "="*100)
            print(f"{'Orden':<10} {'Total Pago':<15} {'Abonado':<15} {'Saldo':<15} {'Proyecto'}")
            print("="*100)
            
            total_saldo = 0
            for pago in pagos:
                orden = pago.get("orden_numero")
                total = pago.get("total_pago", 0)
                abonado = pago.get("total_abonado", 0)
                saldo = pago.get("saldo_pendiente", 0)
                proyecto = pago.get("proyecto_nombre", "")
                
                print(f"{orden:<10} ${total:>13,} ${abonado:>13,} ${saldo:>13,} {proyecto}")
                total_saldo += saldo
            
            print("="*100)
            print(f"{'TOTAL':<10} {'':<15} {'':<15} ${total_saldo:>13,}")
            print("="*100)
        else:
            print(f"Error: {data.get('message')}")
    else:
        print(f"Error HTTP: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
