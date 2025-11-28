import requests
import json

# URL para consultar abonos de orden específica
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJub21icmUiOiJDQVJMT1MgQUxFR1JJQSIsImV4cCI6MTc2MjM5MTk3Nn0.wgk8nkRkbWHIdi0fB8XSLD-Iv0cnLOepQk-NqdFdgTU"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Órdenes a verificar
ordenes = [3237, 3205, 3144, 3126]

print("="*80)
print("VERIFICACIÓN DE ABONOS EN LA BASE DE DATOS")
print("="*80)

for orden in ordenes:
    url = f"http://localhost:5001/api/pagos/abonos/{orden}"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            abonos = data.get("data", [])
            
            print(f"\n📝 ORDEN {orden}:")
            print(f"   Total de registros de abonos: {len(abonos)}")
            
            if abonos:
                print(f"   {'ID':<8} {'Monto':<15} {'Fecha':<15} {'Observación'}")
                print("   " + "-"*70)
                total_suma = 0
                for ab in abonos:
                    monto = ab.get("monto_abono", 0)
                    total_suma += monto
                    print(f"   {ab.get('id'):<8} ${monto:>12,} {ab.get('fecha_abono', ''):<15} {ab.get('observacion', '')[:30]}")
                print("   " + "-"*70)
                print(f"   {'TOTAL':<8} ${total_suma:>12,}")
            else:
                print("   No hay abonos registrados")
                
    except Exception as e:
        print(f"Error al consultar orden {orden}: {e}")

print("\n" + "="*80)
