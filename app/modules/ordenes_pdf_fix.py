# Versión mejorada del PDF para órdenes de compra

import io
import re
from datetime import date
from flask import current_app, request, Response
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm


def parse_monto(x):
    """Convierte un string tipo "$1.234.567,89" a float 1234567.89"""
    if not x:
        return 0.0
    # Limpiar el string
    limpio = re.sub(r'[^\d,\.]', '', str(x))
    partes = limpio.split(',')
    if len(partes) > 1:
        # Tiene decimales
        dec = partes[-1]
        ent = ''.join(partes[:-1])
        limpio2 = ent.replace('.', '') + '.' + dec
    else:
        # Sin decimales, quitar puntos (miles)
        limpio2 = partes[0].replace('.', '')
    try:
        return float(limpio2)
    except ValueError:
        return 0.0


def formato_pesos(valor):
    """Formatea un número a pesos chilenos"""
    try:
        return "${:,.0f}".format(float(valor)).replace(",", ".")
    except Exception:
        return "$0"


def generate_pdf_improved():
    """Genera PDF mejorado con manejo de errores"""
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=15 * mm, leftMargin=15 * mm,
            topMargin=20 * mm, bottomMargin=30 * mm
        )

        supabase = current_app.config['SUPABASE']

        # ——— Recoger datos del formulario con validación ———
        orden_compra = request.form.get("next_num", "")
        tipo_entrega = request.form.get("tipo_entrega", "")
        plazo_pago = request.form.get("plazo_pago", "")
        sin_iva = request.form.get("sin_iva") is not None
        observaciones = request.form.get("observaciones", "")

        # Debug: Ver qué datos están llegando
        current_app.logger.info(f"Generando PDF - Orden: {orden_compra}")
        current_app.logger.info(f"Form data keys: {list(request.form.keys())}")

        # --- Obtener nombres y RUT desde Supabase ---
        proveedor_id = request.form.get("proveedor_id")
        proveedor_nombre = "Proveedor no especificado"
        rut = ""
        if proveedor_id:
            try:
                proveedor_row = supabase.table("proveedores").select("nombre,rut").eq("id", proveedor_id).execute().data
                if proveedor_row:
                    proveedor_nombre = proveedor_row[0]["nombre"]
                    rut = proveedor_row[0]["rut"]
            except Exception as e:
                current_app.logger.error(f"Error obteniendo proveedor: {e}")

        proyecto_id = request.form.get("proyecto_id")
        proyecto = "Proyecto no especificado"
        if proyecto_id:
            try:
                proyecto_row = supabase.table("proyectos").select("proyecto").eq("id", proyecto_id).execute().data
                if proyecto_row:
                    proyecto = proyecto_row[0]["proyecto"]
            except Exception as e:
                current_app.logger.error(f"Error obteniendo proyecto: {e}")

        solicitante_id = request.form.get("solicitado_por")
        solicitante = "Solicitante no especificado"
        if solicitante_id:
            try:
                trabajador_row = supabase.table("trabajadores").select("nombre").eq("id", solicitante_id).execute().data
                if trabajador_row:
                    solicitante = trabajador_row[0]["nombre"]
            except Exception as e:
                current_app.logger.error(f"Error obteniendo trabajador: {e}")

        # Obtener líneas del formulario
        cods = request.form.getlist("cod_linea[]")
        descs = request.form.getlist("desc_linea[]")
        qtys = request.form.getlist("cant_linea[]")
        netos = request.form.getlist("neto_linea[]")
        totals = request.form.getlist("total_linea[]")

        current_app.logger.info(f"Líneas encontradas: {len(cods)} códigos, {len(descs)} descripciones")

        # Construir líneas para ReportLab con validación
        lineas = []
        for i, (cod, desc, qty, net, tot) in enumerate(zip(cods, descs, qtys, netos, totals)):
            try:
                if desc and qty and qty.strip() and float(qty) > 0:
                    lineas.append([
                        cod or f"COD-{i+1}",
                        desc,
                        int(float(qty)),
                        parse_monto(net),
                        parse_monto(tot)
                    ])
            except (ValueError, TypeError) as e:
                current_app.logger.warning(f"Error procesando línea {i}: {e}")
                continue

        # Si no hay líneas válidas, crear una línea de ejemplo
        if not lineas:
            lineas = [["", "Sin productos especificados", 0, 0, 0]]

        # ——— Crear estilos ———
        styles = getSampleStyleSheet()
        normal = styles["Normal"]
        h1 = styles["Heading1"]
        h2 = styles["Heading2"]

        # Estilo para las condiciones
        cond_style = ParagraphStyle(
            "Condiciones", parent=normal,
            fontSize=6, leading=8, alignment=TA_JUSTIFY
        )
        condiciones = [
            "1. La presente Orden de Compra (OC) podrá ser modificada, ajustada o terminada por Somyl S.A. en cualquier momento, de manera total o parcial, sin alegación de motivo o causa alguna, mediante la notificación escrita física o por correo electrónico al proveedor con una anticipación de 5 (cinco) días.",
            "2. La presente Orden de Compra no obliga a Somyl S.A. a adquirir o comprar la totalidad de esta; el pago efectivo estará definido cuando el proveedor entregue la GUIA DE DESPACHO o DOCUMENTO DE ACEPTACIÓN relacionada a la OC y aceptada por Somyl S.A.",
            "3. Los servicios o material suministrados bajo esta OC tendrán una garantía de 3 Meses o hasta la aceptación total del cliente final de Somyl S.A.",
            "4. El proveedor emitirá su factura después de recibir firmada la GUIA DE DESPACHO o notificación oficial por correo electrónico por parte del área de administración de Somyl S.A. El Subcontratista debe incluir todos los impuestos del gobierno, gravámenes y tasas que correspondan. En caso de no contar con la notificación y proceder a realizar la factura, el proveedor no tiene derecho de reclamo o denuncia de incumplimiento de pago en el plazo que corresponda; este plazo se ajustará una vez Somyl S.A. acepte dicha factura.",
            "5. Toda factura emitida a Somyl S.A. debe ser enviada al Departamento de Administración al correo electrónico indicado en esta OC."
        ]
        cond_para = Paragraph("<br/>".join(condiciones), cond_style)

        # ——— Pie de página ———
        def draw_footer(canvas, doc):
            width, height = A4
            cw = width - doc.leftMargin - doc.rightMargin

            # Línea horizontal para firmas
            line_y = 35 * mm
            canvas.saveState()
            canvas.setStrokeColor(colors.black)
            canvas.line(doc.leftMargin, line_y, doc.leftMargin + cw, line_y)
            canvas.restoreState()

            # Texto de firmas
            canvas.setFont("Helvetica", 10)
            canvas.drawCentredString(doc.leftMargin + cw * 0.25, line_y + 2 * mm, "Luis Medina")
            canvas.drawCentredString(doc.leftMargin + cw * 0.75, line_y + 2 * mm, "Aprobación de Gerencia")

            # Condiciones
            cond_y = line_y - 4 * mm
            try:
                cond_para.wrapOn(canvas, cw, height)
                cond_para.drawOn(canvas, doc.leftMargin, cond_y - cond_para.height)
            except Exception as e:
                current_app.logger.error(f"Error dibujando condiciones: {e}")

        # ——— Construir contenido ———
        story = []

        # Encabezado de la empresa
        emisora = [
            Paragraph("SOMYL S.A.", h2),
            Paragraph("RUT: 76.002.581-K", normal),
            Paragraph("Giro: TELECOMUNICACIONES", normal),
            Paragraph("PUERTA ORIENTE 361 OF 311 B TORRE B COLINA", normal),
            Paragraph("FONO: 232642974", normal),
        ]
        
        # Fecha
        meses = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]
        hoy = date.today()
        fecha_str = f"{hoy.day} de {meses[hoy.month - 1]} de {hoy.year}"

        # Tabla de encabezado
        header_data = [
            [
                emisora,
                [
                    Paragraph("ORDEN DE COMPRA", h1),
                    Paragraph(f"N° {orden_compra}", normal),
                    Paragraph(f"Fecha: {fecha_str}", normal),
                ]
            ]
        ]
        header_tbl = Table(header_data, colWidths=[100 * mm, 70 * mm])
        header_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.extend([header_tbl, Spacer(1, 6)])

        # Línea horizontal
        hr = Table([[""]], colWidths=[170 * mm])
        hr.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.black)]))
        story.extend([hr, Spacer(1, 12)])

        # Información del proveedor y orden
        info_texts = [
            f"<b>Señores:</b> {proveedor_nombre} (RUT: {rut})",
            f"<b>Tipo de Entrega:</b> {tipo_entrega}",
            f"<b>Plazo de Pago:</b> {plazo_pago}" + (" (Sin IVA)" if sin_iva else ""),
            f"<b>Proyecto:</b> {proyecto}",
            f"<b>Solicitado por:</b> {solicitante}"
        ]
        for txt in info_texts:
            story.append(Paragraph(txt, normal))
        story.append(Spacer(1, 12))

        # ——— Tabla de líneas ———
        data = [["CÓDIGO", "DESCRIPCIÓN", "CANTIDAD", "NETO", "TOTAL"]]
        for ln in lineas:
            desc_para = Paragraph(str(ln[1]), normal)
            data.append([
                str(ln[0]),
                desc_para,
                str(ln[2]),
                formato_pesos(ln[3]),
                formato_pesos(ln[4])
            ])

        tbl = Table(
            data,
            colWidths=[25 * mm, 80 * mm, 20 * mm, 25 * mm, 25 * mm]
        )
        tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (2, 1), (4, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ]))
        story.extend([tbl, Spacer(1, 12)])

        # ——— Observaciones ———
        if observaciones:
            story.extend([
                Paragraph("<b>Observaciones:</b>", normal),
                Paragraph(observaciones, normal),
                Spacer(1, 12)
            ])

        # ——— Calcular totales ———
        total_neto = sum(ln[4] for ln in lineas)
        iva = round(total_neto * 0.19) if not sin_iva else 0
        total_final = total_neto + iva

        totales_tbl = Table([
            ["", "Total Neto:", formato_pesos(total_neto)],
            ["", "IVA (19%):", formato_pesos(iva)],
            ["", "Total:", formato_pesos(total_final)],
        ], colWidths=[100*mm, 35*mm, 35*mm])
        totales_tbl.setStyle(TableStyle([
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.extend([totales_tbl, Spacer(1, 12)])

        # Espacio para firmas
        story.append(Spacer(1, 20 * mm))

        # ——— Construir PDF ———
        doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)

        pdf = buffer.getvalue()
        buffer.close()

        # Nombre del archivo
        filename = f"O. Compra {orden_compra} {proveedor_nombre}.pdf"
        # Limpiar caracteres especiales del filename
        filename = re.sub(r'[^\w\s\-\.]', '', filename)
        
        return Response(
            pdf,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    except Exception as e:
        current_app.logger.error(f"Error generando PDF: {e}")
        return Response(
            f"Error generando PDF: {str(e)}",
            status=500,
            mimetype="text/plain"
        )
