from flask import Blueprint, request, current_app, jsonify
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from datetime import date
import io
from flask import make_response

bp_pdf_reportlab = Blueprint(
    'ordenes_pago_pdf_reportlab', 
    __name__,
    template_folder='../templates/ordenes_pago'
)

def safe_float(value, default=0.0):
    """Convierte un valor a float de manera segura"""
    if not value or str(value).strip() == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Convierte un valor a int de manera segura"""
    if not value or str(value).strip() == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def format_currency(amount):
    """Formatea un monto como moneda chilena sin decimales"""
    return f"${amount:,.0f}"

@bp_pdf_reportlab.route('/ordenes_pago/pdf_reportlab', methods=['POST'], endpoint='pdf_reportlab')
def generar_pdf_reportlab():
    """Genera PDF usando ReportLab como alternativa a wkhtmltopdf"""
    try:
        supabase = current_app.config['SUPABASE']
        f = request.form

        # Leer datos del formulario
        numero = safe_int(f.get('next_num', '0'))
        nombre_proveedor = f.get('nombre_proveedor', '')
        detalle_op = f.get('detalle_compra', '')
        fecha_venc = f.get('vencimiento', '')
        fecha_factura = f.get('fecha_factura', '')
        autoriza_nombre = f.get('autoriza_input', '')
        autoriza_email = f.get('autoriza_email', '')

        # Totales
        total_neto = safe_float(f.get('total_neto', '0'))
        total_iva = safe_float(f.get('total_iva', '0'))
        total_pagar = safe_float(f.get('total_pagar', '0'))

        # Listas de detalle
        ocs = f.getlist('orden_compra[]')
        guias = f.getlist('guia_recepcion[]')
        descripciones = f.getlist('descripcion[]')

        # Verificar IVA
        sin_iva = False
        if ocs:
            try:
                oc_numbers = [int(oc) for oc in ocs if oc.isdigit()]
                if oc_numbers:
                    oc_rows = (
                        supabase.table('orden_de_compra')
                                .select('fac_sin_iva')
                                .in_('orden_compra', oc_numbers)
                                .execute()
                                .data
                    ) or []
                    
                    for oc_row in oc_rows:
                        if oc_row.get('fac_sin_iva', 0):
                            sin_iva = True
                            break
            except Exception as e:
                current_app.logger.error(f"Error verificando IVA: {e}")

        # Ajustar totales si es sin IVA
        if sin_iva:
            total_iva = 0
            total_pagar = total_neto

        # Obtener datos del proveedor
        prov_rows = (
            supabase.table('proveedores')
                    .select('paguese_a, rut, cuenta, banco, correo')
                    .eq('nombre', nombre_proveedor)
                    .limit(1)
                    .execute()
                    .data
        ) or []
        prov = prov_rows[0] if prov_rows else {}

        # Crear PDF en memoria
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []

        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        normal_style = styles['Normal']
        normal_style.fontSize = 10
        
        # Título principal
        story.append(Paragraph("ORDEN DE PAGO", title_style))
        story.append(Spacer(1, 20))

        # Información de la empresa
        empresa_data = [
            ["EMPRESA:", "Somyl S.A."],
            ["RUT:", "76.002.581-K"],
            ["DIRECCIÓN:", "PUERTA ORIENTE 361 OF 311 B TORRE B COLINA"],
            ["TELÉFONO:", "232642974"]
        ]
        
        empresa_table = Table(empresa_data, colWidths=[1.5*inch, 4*inch])
        empresa_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(empresa_table)
        story.append(Spacer(1, 20))

        # Información del proveedor
        proveedor_data = [
            ["PROVEEDOR:", nombre_proveedor],
            ["PAGUESE A:", prov.get('paguese_a', '')],
            ["RUT:", prov.get('rut', '')],
            ["BANCO:", prov.get('banco', '')],
            ["CUENTA:", prov.get('cuenta', '')],
            ["CORREO:", prov.get('correo', '')]
        ]
        
        proveedor_table = Table(proveedor_data, colWidths=[1.5*inch, 4*inch])
        proveedor_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(proveedor_table)
        story.append(Spacer(1, 20))

        # Información de la orden
        orden_data = [
            ["ORDEN N°:", str(numero)],
            ["FECHA EMISIÓN:", date.today().strftime('%d/%m/%Y')],
            ["FECHA VENCIMIENTO:", fecha_venc],
            ["FECHA FACTURA:", fecha_factura],
            ["DETALLE:", detalle_op]
        ]
        
        orden_table = Table(orden_data, colWidths=[1.5*inch, 4*inch])
        orden_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(orden_table)
        story.append(Spacer(1, 20))

        # Detalle de materiales
        if guias and ocs and descripciones:
            story.append(Paragraph("DETALLE DE MATERIALES", styles['Heading2']))
            
            detalle_data = [["GUÍA/FACTURA", "ORDEN COMPRA", "DESCRIPCIÓN"]]
            for guia, oc, desc in zip(guias, ocs, descripciones):
                detalle_data.append([guia, oc, desc])
            
            detalle_table = Table(detalle_data, colWidths=[1.5*inch, 1.5*inch, 3*inch])
            detalle_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(detalle_table)
            story.append(Spacer(1, 20))

        # Totales
        totales_data = [
            ["TOTAL NETO:", format_currency(total_neto)],
            ["IVA (19%):" if not sin_iva else "IVA:", format_currency(total_iva)],
            ["TOTAL A PAGAR:", format_currency(total_pagar)]
        ]
        
        if sin_iva:
            totales_data.insert(1, ["ESTADO IVA:", "SIN IVA"])
        
        totales_table = Table(totales_data, colWidths=[2*inch, 2*inch])
        totales_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(totales_table)
        story.append(Spacer(1, 30))

        # Autorización
        if autoriza_nombre:
            story.append(Paragraph("AUTORIZADO POR:", styles['Heading3']))
            story.append(Paragraph(f"Nombre: {autoriza_nombre}", normal_style))
            story.append(Paragraph(f"Email: {autoriza_email}", normal_style))

        # Generar PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        # Respuesta
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        safe_name = prov.get('paguese_a', '').replace(' ', '_').replace('/', '_')
        filename = f"orden_pago_{numero}_{safe_name}.pdf"
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        current_app.logger.info(f"PDF generado exitosamente con ReportLab para orden {numero}")
        return response

    except Exception as e:
        current_app.logger.error(f"Error generando PDF con ReportLab: {e}")
        return jsonify({
            'error': 'Error generando PDF',
            'message': str(e),
            'suggestion': 'Contacte al administrador del sistema'
        }), 500
