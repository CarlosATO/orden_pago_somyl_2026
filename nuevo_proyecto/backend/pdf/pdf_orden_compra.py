"""Generador de PDF para Órdenes de Compra - Versión Final.

Mejoras implementadas:
- Texto legal justificado (cuadrado) y siempre visible en el pie de página
- Línea de firma más abajo para tener espacio físico para firmar
- Diseño profesional y elegante con mejor tipografía
- Colores corporativos y mejor contraste visual
- Protección contra errores de tipo (todos los strings convertidos)
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Frame
from reportlab.lib.units import mm, inch
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
import os

def generar_pdf_orden_compra(datos_orden):
    """
    Genera un PDF de Orden de Compra profesional
    
    Args:
        datos_orden: Dict con los datos de la orden
    
    Returns:
        str: Ruta del archivo PDF generado
    """
    # Crear directorio para PDFs
    pdf_dir = os.path.join(os.path.dirname(__file__), '..', 'pdfs_generados')
    os.makedirs(pdf_dir, exist_ok=True)
    
    # IMPORTANTE: Convertir a string para evitar errores
    numero_oc = str(datos_orden.get('numero_oc', 'SIN_NUMERO'))
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"OC_{numero_oc}_{timestamp}.pdf"
    filepath = os.path.join(pdf_dir, filename)
    
    # AJUSTE: Margen inferior más grande para el texto legal
    bottom_margin = 70 * mm
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=bottom_margin
    )

    elements = []
    
    # --- ESTILOS MEJORADOS ---
    styles = getSampleStyleSheet()
    
    # Colores corporativos profesionales
    COLOR_PRIMARY = colors.HexColor('#2C3E50')
    COLOR_SECONDARY = colors.HexColor('#34495E')
    COLOR_ACCENT = colors.HexColor('#3498DB')
    COLOR_HEADER_BG = colors.HexColor('#ECF0F1')
    
    styles.add(ParagraphStyle(
        name='RightSmall',
        parent=styles['Normal'],
        alignment=TA_RIGHT,
        fontSize=9,
        textColor=COLOR_SECONDARY
    ))
    
    styles.add(ParagraphStyle(
        name='Small',
        parent=styles['Normal'],
        fontSize=9,
        textColor=COLOR_SECONDARY,
        leading=12
    ))
    
    styles.add(ParagraphStyle(
        name='CompanyName',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=COLOR_PRIMARY,
        spaceAfter=2,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='HeaderTitle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=13,
        textColor=COLOR_PRIMARY,
        fontName='Helvetica-Bold'
    ))
    
    # AJUSTE: Texto legal JUSTIFICADO
    styles.add(ParagraphStyle(
        name='Legal',
        parent=styles['Normal'],
        fontSize=7,
        alignment=TA_JUSTIFY,  # ✅ TEXTO JUSTIFICADO (cuadrado)
        leading=8.5,
        textColor=colors.HexColor('#555555'),
        leftIndent=0,
        rightIndent=0
    ))
    
    styles.add(ParagraphStyle(
        name='SectionLabel',
        parent=styles['Normal'],
        fontSize=9,
        textColor=COLOR_PRIMARY,
        fontName='Helvetica-Bold'
    ))

    def fmt_money(value):
        try:
            n = float(value)
        except Exception:
            n = 0
        text = f"{n:,.0f}".replace(',', '.')
        return f"${text}"

    def to_number(value):
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip().replace('$', '').replace(' ', '')
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        else:
            if s.count('.') > 0 and s.count(',') == 0:
                s = s.replace('.', '')
            if s.count(',') > 0 and s.count('.') == 0:
                s = s.replace(',', '.')
        try:
            return float(s)
        except Exception:
            return 0.0

    # --- ENCABEZADO MEJORADO ---
    empresa = datos_orden.get('empresa', {})
    empresa_nombre = str(empresa.get('nombre', 'SOMYL S.A.'))
    empresa_rut = str(empresa.get('rut', 'RUT: 76.000.581-K'))
    empresa_direccion = str(empresa.get('direccion', 'Puerta Oriente 361 Of 311 Torre B Colina'))
    empresa_telefono = str(empresa.get('telefono', 'FONO: 232342974'))

    left_header = Paragraph(
        f"<font color='#2C3E50' size='14'><b>{empresa_nombre}</b></font><br/>"
        f"<font color='#555555' size='8'>{empresa_rut}<br/>{empresa_direccion}<br/>{empresa_telefono}</font>",
        styles['Small']
    )

    right_header_data = [
        [Paragraph('<b>ORDEN DE COMPRA</b>', styles['HeaderTitle'])],
        [Table([
            [Paragraph('<b>N° OC:</b>', styles['SectionLabel']), Paragraph(numero_oc, styles['Small'])],
            [Paragraph('<b>Fecha:</b>', styles['SectionLabel']), 
             Paragraph(str(datos_orden.get('fecha', datetime.now().strftime('%d-%m-%Y'))), styles['Small'])]
        ], colWidths=[25*mm, 40*mm])]
    ]
    
    right_header = Table(right_header_data, colWidths=[65*mm])
    right_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_HEADER_BG),
        ('BOX', (0,0), (-1,-1), 1.5, COLOR_PRIMARY),
        ('TOPPADDING', (0,0), (-1,0), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))

    header_table = Table([[left_header, right_header]], colWidths=[doc.width*0.55, doc.width*0.45])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT')
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 8*mm))

    # --- DATOS DEL PROVEEDOR MEJORADOS ---
    proveedor = datos_orden.get('proveedor', {})
    proveedor_data = [
        [Paragraph('<b>Señores:</b>', styles['SectionLabel']), 
         Paragraph(str(proveedor.get('nombre', 'N/A')), styles['Small'])],
        [Paragraph('<b>RUT:</b>', styles['SectionLabel']), 
         Paragraph(str(proveedor.get('rut', 'N/A')), styles['Small'])],
        [Paragraph('<b>Tipo de Entrega:</b>', styles['SectionLabel']), 
         Paragraph(str(datos_orden.get('tipo_entrega', '---')), styles['Small'])],
        [Paragraph('<b>Plazo de Pago:</b>', styles['SectionLabel']), 
         Paragraph(str(datos_orden.get('plazo_pago', '---')), styles['Small'])],
        [Paragraph('<b>Proyecto:</b>', styles['SectionLabel']), 
         Paragraph(str(datos_orden.get('proyecto', '---')), styles['Small'])],
        [Paragraph('<b>Solicitado por:</b>', styles['SectionLabel']), 
         Paragraph(str(datos_orden.get('solicitado_por', '---')), styles['Small'])]
    ]

    tabla_proveedor = Table(proveedor_data, colWidths=[40*mm, doc.width-40*mm])
    tabla_proveedor.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LINEBELOW', (0,-1), (-1,-1), 0.5, colors.HexColor('#CCCCCC'))
    ]))
    elements.append(tabla_proveedor)
    elements.append(Spacer(1, 5*mm))

    # --- TABLA DE PRODUCTOS PROFESIONAL ---
    productos = datos_orden.get('productos', [])
    datos_productos = [[
        Paragraph('<b>CÓDIGO</b>', styles['SectionLabel']),
        Paragraph('<b>DESCRIPCIÓN</b>', styles['SectionLabel']),
        Paragraph('<b>CANT.</b>', styles['SectionLabel']),
        Paragraph('<b>PRECIO UNIT.</b>', styles['SectionLabel']),
        Paragraph('<b>TOTAL</b>', styles['SectionLabel'])
    ]]

    for prod in productos:
        codigo = str(prod.get('codigo', ''))
        descripcion = str(prod.get('descripcion', ''))
        cantidad_raw = prod.get('cantidad', 0)
        neto_raw = prod.get('precio', prod.get('netoUnitario', 0))
        total_raw = prod.get('total', None)

        cantidad = to_number(cantidad_raw)
        neto = to_number(neto_raw)
        if total_raw is None:
            total_line = cantidad * neto
        else:
            total_line = to_number(total_raw)

        datos_productos.append([
            Paragraph(codigo, styles['Small']),
            Paragraph(descripcion, styles['Small']),
            Paragraph(str(int(cantidad)) if cantidad.is_integer() else str(cantidad), styles['Small']),
            Paragraph(fmt_money(neto), styles['RightSmall']),
            Paragraph(fmt_money(total_line), styles['RightSmall'])
        ])

    col_widths = [25*mm, doc.width - (25*mm + 25*mm + 32*mm + 32*mm), 25*mm, 32*mm, 32*mm]
    tabla_productos = Table(datos_productos, colWidths=col_widths, repeatRows=1)
    tabla_productos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DDDDDD')),
        ('LINEBELOW', (0,0), (-1,0), 1.5, COLOR_PRIMARY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (2,0), (2,-1), 'CENTER'),
        ('ALIGN', (3,0), (4,-1), 'RIGHT'),
        ('ALIGN', (0,0), (1,-1), 'LEFT'),
        ('TOPPADDING', (0,1), (-1,-1), 6),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9F9')])
    ]))
    elements.append(tabla_productos)
    elements.append(Spacer(1, 5*mm))

    # Observaciones
    observ = datos_orden.get('observaciones', '')
    if observ:
        elements.append(Paragraph(f"<b>Observaciones:</b> {str(observ)}", styles['Small']))
        elements.append(Spacer(1, 6*mm))

    # --- TOTALES ELEGANTES ---
    subtotal = datos_orden.get('subtotal', 0)
    iva = datos_orden.get('iva', 0)
    total = datos_orden.get('total', 0)

    datos_totales = [
        ['', '', Paragraph('<b>Total Neto:</b>', styles['SectionLabel']), 
         Paragraph(fmt_money(subtotal), styles['RightSmall'])],
        ['', '', Paragraph('<b>IVA (19%):</b>', styles['SectionLabel']), 
         Paragraph(fmt_money(iva), styles['RightSmall'])],
        ['', '', Paragraph('<b>TOTAL:</b>', styles['SectionLabel']), 
         Paragraph(f"<font size='11' color='#2C3E50'><b>{fmt_money(total)}</b></font>", styles['RightSmall'])]
    ]

    tabla_totales = Table(datos_totales, colWidths=[doc.width*0.45, 15*mm, 35*mm, 35*mm])
    tabla_totales.setStyle(TableStyle([
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LINEABOVE', (2,2), (-1,2), 1, COLOR_PRIMARY),
        ('BACKGROUND', (2,2), (-1,2), COLOR_HEADER_BG)
    ]))
    elements.append(tabla_totales)
    elements.append(Spacer(1, 15*mm))

    # --- FIRMAS CON ESPACIO PARA FIRMAR FÍSICAMENTE ---
    # AJUSTE: Línea más abajo para tener espacio de firma
    firma_names = [
        Paragraph('<b>Luis Medina</b><br/><font size="8">Responsable de Compras</font>', styles['Small']), 
        Paragraph('<b>Aprobación de Gerencia</b><br/><font size="8">Gerente General</font>', styles['Small'])
    ]
    
    firma_table = Table(
        [[firma_names[0], firma_names[1]], ['', '']], 
        colWidths=[doc.width*0.5-6*mm, doc.width*0.5-6*mm],
        rowHeights=[None, 20*mm]  # ✅ Más espacio entre nombres y línea
    )
    firma_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('LINEABOVE', (0,1), (-1,1), 1, COLOR_SECONDARY),  # Línea arriba de la fila vacía
        ('TOPPADDING', (0,1), (-1,1), 0),  # Sin padding para que línea esté más abajo
        ('VALIGN', (0,0), (-1,0), 'TOP')  # Nombres arriba
    ]))
    elements.append(firma_table)

    # Texto legal
    legal_text = str(datos_orden.get('texto_legal', """<b>TÉRMINOS Y CONDICIONES</b><br/><br/>
1. La presente Orden de Compra (OC) podrá ser modificada, ajustada o terminada por Somyl S.A. en cualquier momento, de manera total o parcial, sin alegación de motivo o causa alguna, mediante la notificación escrita física o por correo electrónico al proveedor con una anticipación de 5 (cinco) días.<br/><br/>
2. La presente Orden de Compra no obliga a Somyl S.A. a adquirir o comprar la totalidad de esta; el pago efectivo estará definido cuando el proveedor entregue la GUIA DE DESPACHO o DOCUMENTO DE ACEPTACIÓN relacionada a la OC y aceptada por Somyl S.A.<br/><br/>
3. Los servicios o material suministrados bajo esta OC tendrán una garantía de 3 Meses o hasta la aceptación total del cliente final de Somyl S.A.<br/><br/>
4. El proveedor emitirá su factura después de recibir firmada la GUIA DE DESPACHO o notificación oficial por correo electrónico por parte del área de administración de Somyl S.A. El Subcontratista debe incluir todos los impuestos del gobierno, gravámenes y tasas que correspondan. En caso de no contar con la notificación y proceder a realizar la factura, el proveedor no tiene derecho de reclamo o denuncia de incumplimiento de pago en el plazo que corresponda; este plazo se ajustará una vez Somyl S.A. acepte dicha factura.<br/><br/>
5. Toda factura emitida a Somyl S.A. debe ser enviada al Departamento de Administración al correo electrónico indicado en esta OC."""))

    # Footer con texto legal justificado
    def draw_footer(canvas, doc_obj):
        canvas.saveState()
        
        # Línea separadora elegante
        canvas.setStrokeColor(COLOR_SECONDARY)
        canvas.setLineWidth(0.5)
        canvas.line(
            doc_obj.leftMargin, 
            bottom_margin - 5*mm, 
            A4[0] - doc_obj.rightMargin, 
            bottom_margin - 5*mm
        )
        
        # Frame para el texto legal JUSTIFICADO
        footer_width = doc_obj.width
        x = doc_obj.leftMargin
        footer_y = 8 * mm
        footer_height = bottom_margin - 10*mm
        
        footer_frame = Frame(x, footer_y, footer_width, footer_height, 
                            leftPadding=0, rightPadding=0, 
                            topPadding=3*mm, bottomPadding=0,
                            showBoundary=0)
        
        p = Paragraph(legal_text, styles['Legal'])  # Estilo con TA_JUSTIFY
        footer_frame.addFromList([p], canvas)
        
        canvas.restoreState()

    # Construir PDF
    doc.build(elements, onFirstPage=draw_footer, onLaterPages=draw_footer)

    return filepath