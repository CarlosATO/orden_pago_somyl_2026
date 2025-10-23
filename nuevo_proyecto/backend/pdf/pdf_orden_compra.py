"""
Generador de PDF para Órdenes de Compra
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from datetime import datetime
import os

def generar_pdf_orden_compra(datos_orden):
    """
    Genera un PDF de Orden de Compra
    
    Args:
        datos_orden: Dict con los datos de la orden
        {
            'numero_oc': '3497',
            'proveedor': {'nombre': 'Proveedor X', 'rut': '12345678-9'},
            'fecha': '2025-10-23',
            'productos': [
                {'descripcion': 'Producto 1', 'cantidad': 10, 'precio': 1000, 'total': 10000}
            ],
            'subtotal': 10000,
            'iva': 1900,
            'total': 11900
        }
    
    Returns:
        str: Ruta del archivo PDF generado
    """
    # Crear directorio para PDFs si no existe
    pdf_dir = os.path.join(os.path.dirname(__file__), '..', 'pdfs_generados')
    os.makedirs(pdf_dir, exist_ok=True)
    
    # Nombre del archivo basado en número de OC y fecha
    numero_oc = datos_orden.get('numero_oc', 'SIN_NUMERO')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"OC_{numero_oc}_{timestamp}.pdf"
    filepath = os.path.join(pdf_dir, filename)
    
    # Crear el documento PDF
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    titulo = Paragraph(f"<b>ORDEN DE COMPRA N° {numero_oc}</b>", styles['Title'])
    elements.append(titulo)
    elements.append(Spacer(1, 0.3*inch))
    
    # Información del proveedor
    proveedor = datos_orden.get('proveedor', {})
    info_proveedor = [
        ['Proveedor:', proveedor.get('nombre', 'N/A')],
        ['RUT:', proveedor.get('rut', 'N/A')],
        ['Fecha:', datos_orden.get('fecha', datetime.now().strftime('%Y-%m-%d'))]
    ]
    
    tabla_proveedor = Table(info_proveedor, colWidths=[2*inch, 4*inch])
    tabla_proveedor.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(tabla_proveedor)
    elements.append(Spacer(1, 0.5*inch))
    
    # Tabla de productos
    productos = datos_orden.get('productos', [])
    datos_productos = [['Descripción', 'Cantidad', 'Precio Unit.', 'Total']]
    
    for prod in productos:
        datos_productos.append([
            prod.get('descripcion', ''),
            str(prod.get('cantidad', 0)),
            f"${prod.get('precio', 0):,.0f}",
            f"${prod.get('total', 0):,.0f}"
        ])
    
    tabla_productos = Table(datos_productos, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
    tabla_productos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(tabla_productos)
    elements.append(Spacer(1, 0.3*inch))
    
    # Totales
    subtotal = datos_orden.get('subtotal', 0)
    iva = datos_orden.get('iva', 0)
    total = datos_orden.get('total', 0)
    
    datos_totales = [
        ['', '', 'Subtotal:', f"${subtotal:,.0f}"],
        ['', '', 'IVA (19%):', f"${iva:,.0f}"],
        ['', '', 'TOTAL:', f"${total:,.0f}"]
    ]
    
    tabla_totales = Table(datos_totales, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
    tabla_totales.setStyle(TableStyle([
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LINEABOVE', (2, 2), (-1, 2), 2, colors.black),
        ('BACKGROUND', (2, 2), (-1, 2), colors.lightgrey)
    ]))
    elements.append(tabla_totales)
    
    # Construir el PDF
    doc.build(elements)
    
    return filepath
