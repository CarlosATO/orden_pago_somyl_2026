"""
Generador de PDF para Documentos Pendientes usando ReportLab.
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from datetime import datetime
import os


def fmt_money(value):
    """Formatea un valor como moneda chilena."""
    try:
        n = float(value)
        if n < 0:
            return f"-${abs(n):,.0f}".replace(",", ".")
        return f"${n:,.0f}".replace(",", ".")
    except:
        return "$0"


class NumberedCanvas(canvas.Canvas):
    """Canvas personalizado para agregar número de página y encabezado en cada página."""
    
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self.titulo = kwargs.get('titulo', 'Documentos Pendientes')
        self.fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
        
    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()
        
    def save(self):
        """Agrega el número de página y encabezado a cada página."""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            self.draw_header()
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
        
    def draw_page_number(self, page_count):
        """Dibuja el número de página."""
        self.setFont("Helvetica", 9)
        page_num = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(A4[1] - 15*mm, 10*mm, page_num)
        
    def draw_header(self):
        """Dibuja el encabezado en cada página."""
        self.setFont("Helvetica-Bold", 10)
        self.drawString(15*mm, A4[0] - 15*mm, self.titulo)
        self.setFont("Helvetica", 8)
        self.drawRightString(A4[1] - 15*mm, A4[0] - 15*mm, f"Generado: {self.fecha_generacion}")


def generar_pdf_documentos_pendientes(documentos, stats, filename):
    """
    Genera un PDF con la lista de documentos pendientes.
    
    Args:
        documentos: Lista de documentos pendientes
        stats: Estadísticas (total, pendientes, con_abonos, vencidos)
        filename: Ruta donde guardar el PDF
    """
    from reportlab.platypus import PageBreak
    
    # Crear documento en orientación horizontal (landscape)
    doc = SimpleDocTemplate(
        filename,
        pagesize=landscape(A4),
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=25*mm,
        bottomMargin=20*mm
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#4a5568'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    # Contenido
    story = []
    
    # Título
    titulo = Paragraph("DOCUMENTOS PENDIENTES DE PAGO", title_style)
    story.append(titulo)
    
    # Subtítulo con estadísticas
    fecha_actual = datetime.now().strftime('%d/%m/%Y')
    subtitulo = Paragraph(
        f"Fecha: {fecha_actual} | Total: {stats['total']} documentos "
        f"({stats['pendientes']} pendientes + {stats['con_abonos']} con abonos) | "
        f"Vencidos: {stats['vencidos']}",
        subtitle_style
    )
    story.append(subtitulo)
    story.append(Spacer(1, 10*mm))
    
    # Preparar datos de la tabla
    # Encabezados
    headers = [
        'OP #',
        'Fecha OP',
        'Fecha Venc.',
        'Proveedor',
        'Proyecto',
        'Factura',
        'Monto Total',
        'Abonado',
        'Saldo',
        'Días\nAtraso',
        'Estado'
    ]
    
    data = [headers]
    
    # Datos
    total_monto = 0
    total_abonado = 0
    total_saldo = 0
    
    for documento in documentos:
        monto = float(documento.get('monto_total', 0))
        abonado = float(documento.get('total_abonado', 0))
        saldo = float(documento.get('saldo', 0))
        
        total_monto += monto
        total_abonado += abonado
        total_saldo += saldo
        
        # Estado visual
        dias_atraso = documento.get('dias_atraso', 0)
        if dias_atraso > 0:
            estado = f"VENCIDO\n({dias_atraso} días)"
        else:
            estado = "Al día"
        
        row = [
            str(documento.get('orden_numero', '')),
            documento.get('fecha_op', '---'),
            documento.get('fecha_vencimiento', '---'),
            documento.get('proveedor', '')[:25],  # Limitar largo
            documento.get('proyecto', '')[:20],
            documento.get('factura', '---'),
            fmt_money(monto),
            fmt_money(abonado),
            fmt_money(saldo),
            str(dias_atraso) if dias_atraso > 0 else '-',
            estado
        ]
        data.append(row)
    
    # Fila de totales
    totales = [
        '',
        '',
        '',
        '',
        '',
        'TOTAL:',
        fmt_money(total_monto),
        fmt_money(total_abonado),
        fmt_money(total_saldo),
        '',
        ''
    ]
    data.append(totales)
    
    # Crear tabla
    table = Table(data, repeatRows=1)  # repeatRows=1 repite el encabezado en cada página
    
    # Estilo de la tabla
    table_style = TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Cuerpo
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -2), 7),
        ('ALIGN', (0, 1), (0, -2), 'CENTER'),  # OP #
        ('ALIGN', (1, 1), (2, -2), 'CENTER'),  # Fechas
        ('ALIGN', (6, 1), (8, -2), 'RIGHT'),   # Montos
        ('ALIGN', (9, 1), (9, -2), 'CENTER'),  # Días atraso
        ('ALIGN', (10, 1), (10, -2), 'CENTER'), # Estado
        
        # Bordes
        ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -2), 1, colors.black),
        
        # Fila de totales
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#edf2f7')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 8),
        ('ALIGN', (6, -1), (8, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
        
        # Padding
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ])
    
    # Aplicar colores a filas según días de atraso
    for i, documento in enumerate(documentos, start=1):
        dias_atraso = documento.get('dias_atraso', 0)
        if dias_atraso > 30:
            # Rojo para más de 30 días
            table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fee'))
        elif dias_atraso > 0:
            # Amarillo para vencidos
            table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fffbeb'))
    
    table.setStyle(table_style)
    story.append(table)
    
    # Construir PDF simple (sin NumberedCanvas por ahora)
    doc.build(story)
    
    return filename
