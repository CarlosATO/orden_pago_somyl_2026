"""Generador de PDF para Órdenes de Compra.

Adaptado para formato A4 con layout similar a la imagen de ejemplo:
- Encabezado (empresa / RUT / dirección) a la izquierda y recuadro con N° OC / fecha a la derecha
- Datos del proveedor y metadatos
- Tabla de líneas con encabezado repetido en páginas largas
- Totales alineados a la derecha, espacio para firmas y texto legal en el pie
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.units import mm, inch
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
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
    
    # Crear el documento PDF en A4
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    elements = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='RightSmall', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=9))
    styles.add(ParagraphStyle(name='Small', parent=styles['Normal'], fontSize=9))
    styles.add(ParagraphStyle(name='HeaderTitle', parent=styles['Heading1'], alignment=TA_RIGHT, fontSize=12))

    def fmt_money(value):
        try:
            n = float(value)
        except Exception:
            n = 0
        # Formato con separador de miles como punto y sin decimales: 150.000
        text = f"{n:,.0f}".replace(',', '.')
        return f"${text}"

    # --- Encabezado: izquierda con empresa, derecha con N° OC / Fecha ---
    empresa_lines = []
    empresa = datos_orden.get('empresa', {})
    empresa_nombre = empresa.get('nombre', 'SOMYL S.A.')
    empresa_rut = empresa.get('rut', 'RUT: 76.000.581-K')
    empresa_direccion = empresa.get('direccion', 'Puerta Oriente 361 Of 311 Torre B Colina')
    empresa_telefono = empresa.get('telefono', 'FONO: 232342974')

    left_header = Paragraph(f"<b>{empresa_nombre}</b><br/>{empresa_rut}<br/>{empresa_direccion}<br/>{empresa_telefono}", styles['Small'])

    right_header_data = [
        ['ORDEN DE COMPRA', ''],
        ['N\u00ba OC:', numero_oc],
        ['Fecha:', datos_orden.get('fecha', datetime.now().strftime('%d-%m-%Y'))]
    ]
    right_header = Table(right_header_data, colWidths=[30*mm, 40*mm])
    right_header.setStyle(TableStyle([
        ('SPAN', (0,0), (-1,0)),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,1), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 9)
    ]))

    header_table = Table([[left_header, right_header]], colWidths=[doc.width*0.6, doc.width*0.4])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(header_table)
    elements.append(Spacer(1, 6*mm))

    # --- Datos del proveedor y metadatos ---
    proveedor = datos_orden.get('proveedor', {})
    proveedor_data = [
        ['Señores:', proveedor.get('nombre', 'N/A')],
        ['RUT:', proveedor.get('rut', 'N/A')],
        ['Tipo de Entrega:', datos_orden.get('tipo_entrega', '---')],
        ['Plazo de Entrega:', datos_orden.get('plazo_entrega', '---')],
        ['Proyecto:', datos_orden.get('proyecto', '---')],
        ['Solicitado por:', datos_orden.get('solicitado_por', '---')]
    ]

    tabla_proveedor = Table(proveedor_data, colWidths=[35*mm, doc.width-35*mm])
    tabla_proveedor.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4)
    ]))
    elements.append(tabla_proveedor)
    elements.append(Spacer(1, 4*mm))

    # --- Tabla de productos ---
    productos = datos_orden.get('productos', [])
    datos_productos = [['CÓDIGO', 'DESCRIPCIÓN', 'CANTIDAD', 'NETO', 'TOTAL']]

    for prod in productos:
        codigo = prod.get('codigo', '')
        descripcion = prod.get('descripcion', '')
        cantidad = prod.get('cantidad', 0)
        neto = prod.get('precio', prod.get('netoUnitario', 0))
        total_line = prod.get('total', cantidad * neto)
        datos_productos.append([
            codigo,
            Paragraph(descripcion, styles['Small']),
            str(cantidad),
            fmt_money(neto),
            fmt_money(total_line)
        ])

    col_widths = [25*mm, doc.width - (25*mm + 30*mm + 30*mm + 30*mm), 30*mm, 30*mm, 30*mm]
    tabla_productos = Table(datos_productos, colWidths=col_widths, repeatRows=1)
    tabla_productos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#d3d3d3')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('GRID', (0,0), (-1,-1), 0.25, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (2,1), (2,-1), 'CENTER'),
        ('ALIGN', (3,1), (4,-1), 'RIGHT'),
        ('ALIGN', (0,0), (1,-1), 'LEFT')
    ]))
    elements.append(tabla_productos)
    elements.append(Spacer(1, 4*mm))

    # Observaciones
    observ = datos_orden.get('observaciones', '')
    if observ:
        elements.append(Paragraph(f"<b>Observaciones:</b> {observ}", styles['Small']))
        elements.append(Spacer(1, 6*mm))

    # --- Totales alineados a la derecha ---
    subtotal = datos_orden.get('subtotal', 0)
    iva = datos_orden.get('iva', 0)
    total = datos_orden.get('total', 0)

    datos_totales = [
        [Paragraph('', styles['Small']), Paragraph('', styles['Small']), Paragraph('<b>Total Neto:</b>', styles['Small']), Paragraph(fmt_money(subtotal), styles['RightSmall'])],
        ['', '', Paragraph('<b>IVA (19%):</b>', styles['Small']), Paragraph(fmt_money(iva), styles['RightSmall'])],
        ['', '', Paragraph('<b>Total:</b>', styles['Small']), Paragraph(fmt_money(total), styles['RightSmall'])]
    ]

    tabla_totales = Table(datos_totales, colWidths=[doc.width*0.5, 10*mm, 30*mm, 30*mm])
    tabla_totales.setStyle(TableStyle([
        ('SPAN', (0,0), (1,0)),
        ('SPAN', (0,1), (1,1)),
        ('SPAN', (0,2), (1,2)),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    elements.append(tabla_totales)
    elements.append(Spacer(1, 18*mm))

    # --- Firmas ---
    firma_data = [[Paragraph('<b>_________________________</b>', styles['Small']), Paragraph('<b>_________________________</b>', styles['Small'])],
                  [Paragraph('Luis Medina', styles['Small']), Paragraph('Aprobación de Gerencia', styles['Small'])]]
    firma_table = Table(firma_data, colWidths=[doc.width*0.5-6*mm, doc.width*0.5-6*mm])
    firma_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 9)
    ]))
    elements.append(firma_table)
    elements.append(Spacer(1, 6*mm))

    # --- Texto legal pequeño al pie ---
    legal = datos_orden.get('texto_legal', 'Documento generado automáticamente. Revise condiciones y términos aplicables.')
    elements.append(Paragraph(legal, ParagraphStyle(name='Legal', fontSize=7, alignment=TA_LEFT)))

    # Construir el PDF
    doc.build(elements)

    return filepath
