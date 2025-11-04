"""
Script de prueba para generar un PDF de Orden de Pago refinado
con el nuevo formato que replica el template HTML del sistema antiguo.
"""

import sys
import os

# Agregar el directorio del backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nuevo_proyecto', 'backend'))

from pdf.ordenes_pago_pdf import _generar_pdf_orden_pago

# Datos de prueba completos
datos_orden = {
    "numero_op": 3275,
    "fecha": "03-11-2025",
    "fecha_factura": "25-10-2025",
    "fecha_vencimiento": "30-11-2025",
    "numero_factura": "FAC-12345",
    "oc_principal": "OC-8901",
    "condicion_pago": "30 días",
    "proyecto": "Proyecto Torre Central",
    "empresa": {
        "nombre": "SOMYL S.A.",
        "rut": "76.002.581-K",
        "rubro": "TELECOMUNICACIONES",
        "direccion": "PUERTA ORIENTE 361 OF 311 B TORRE B COLINA",
        "telefono": "232642974"
    },
    "proveedor": {
        "nombre": "C BASAURE SPA",
        "paguese_a": "CRISTIAN BASAURE MARTINEZ",
        "rut": "12.345.678-9",
        "cuenta": "123456789",
        "banco": "Banco de Chile",
        "correo": "contacto@cbasaure.cl"
    },
    "detalle_compra": "Materiales eléctricos para instalación de red de telecomunicaciones en Torre Central. Incluye cables, conectores y equipamiento de respaldo.",
    "autorizador": {
        "nombre": "Juan Pérez Contreras",
        "correo": "juan.perez@somyl.cl"
    },
    "lineas": [
        {
            "oc": "OC-8901",
            "guia": "GR-2024-001",
            "descripcion": "Cable UTP Cat6 x 305m"
        },
        {
            "oc": "OC-8901",
            "guia": "GR-2024-002",
            "descripcion": "Conectores RJ45 x 100 unidades"
        },
        {
            "oc": "OC-8902",
            "guia": "GR-2024-003",
            "descripcion": "Switch 24 puertos Gigabit PoE+"
        },
        {
            "oc": "OC-8902",
            "guia": "GR-2024-004",
            "descripcion": "Rack 42U con accesorios de montaje"
        }
    ],
    "total_neto": 4500000,
    "total_iva": 855000,
    "total_pagar": 5355000
}

print("=" * 60)
print("GENERANDO PDF DE ORDEN DE PAGO - FORMATO REFINADO")
print("=" * 60)
print(f"\nOrden de Pago: #{datos_orden['numero_op']}")
print(f"Proveedor: {datos_orden['proveedor']['nombre']}")
print(f"Total a Pagar: ${datos_orden['total_pagar']:,.0f}".replace(',', '.'))
print(f"\nGenerando PDF...")

try:
    filepath = _generar_pdf_orden_pago(datos_orden)
    print(f"\n✅ PDF generado exitosamente!")
    print(f"📄 Ubicación: {filepath}")
    print(f"📏 Tamaño: {os.path.getsize(filepath):,} bytes".replace(',', '.'))
    
    # Verificar el nombre del archivo
    filename = os.path.basename(filepath)
    expected_pattern = f"orden_pago_{datos_orden['numero_op']}_"
    if filename.startswith(expected_pattern):
        print(f"✅ Nombre de archivo correcto: {filename}")
    else:
        print(f"❌ Nombre de archivo incorrecto. Esperado: {expected_pattern}...")
    
    print("\n" + "=" * 60)
    print("PRUEBA COMPLETADA - Abre el PDF para verificar el formato")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ Error generando PDF: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
