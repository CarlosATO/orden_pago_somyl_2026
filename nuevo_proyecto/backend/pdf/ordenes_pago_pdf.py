"""
Generador de PDF para Órdenes de Pago usando ReportLab.
Similar a pdf_orden_compra.py pero adaptado para órdenes de pago.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT, TA_JUSTIFY
from flask import current_app
from datetime import datetime
import os


def safe_float(value, default=0.0):
    """Convierte un valor a float de forma segura."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    """Convierte un valor a int de forma segura."""
    if value is None or str(value).strip() == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def to_number(value):
    """Convierte cualquier valor a número de forma segura."""
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


def fmt_money(value):
    """Formatea un valor como moneda chilena."""
    try:
        n = float(value)
    except Exception:
        n = 0
    text = f"{n:,.0f}".replace(',', '.')
    return f"${text}"


def _getlist_from_form(form, key):
    """
    Helper para compatibilidad con request.form.getlist y dicts simples.
    Acepta keys como 'orden_compra[]' o 'orden_compra'.
    """
    if hasattr(form, "getlist"):
        return form.getlist(key)
    
    # Primero intentar con el key exacto (puede venir como 'orden_compra[]')
    val = form.get(key)
    
    # Si no existe, intentar sin los corchetes
    if val is None and key.endswith("[]"):
        k = key[:-2]
        val = form.get(k)
    
    # Si aún no existe, intentar con corchetes si no los tenía
    if val is None and not key.endswith("[]"):
        k_with_brackets = key + "[]"
        val = form.get(k_with_brackets)
    
    if val is None:
        return []
    
    # Si viene como string separado por comas
    if isinstance(val, str) and "," in val:
        return [v.strip() for v in val.split(",") if v.strip()]
    
    # Si es lista, devolver tal cual
    if isinstance(val, list):
        return val
    
    return [val]


def generar_pdf_from_form(form):
    """
    Genera un PDF de Orden de Pago a partir de datos de formulario.
    
    Args:
        form: Mapping compatible con request.form (soporta getlist-like y listas)
    
    Returns:
        tuple: (pdf_bytes, filename)
    """
    supabase = current_app.config.get("SUPABASE")
    
    # DEBUG: Mostrar datos recibidos
    current_app.logger.info(f"📋 Datos recibidos para PDF: {list(form.keys())}")
    
    # Leer campos de lista
    ocs = _getlist_from_form(form, "orden_compra[]")
    guias = _getlist_from_form(form, "guia_recepcion[]")
    descripciones = _getlist_from_form(form, "descripcion[]")
    
    current_app.logger.info(f"✅ OCs extraídas: {ocs}")
    current_app.logger.info(f"✅ Guías extraídas: {guias}")
    current_app.logger.info(f"✅ Descripciones extraídas: {descripciones}")
    
    # Leer campos individuales
    numero = safe_int(form.get("next_num", "0"))
    nombre_proveedor = str(form.get("nombre_proveedor", ""))
    detalle_op = str(form.get("detalle_compra", ""))
    fecha_venc = str(form.get("vencimiento", ""))
    fecha_factura = str(form.get("fecha_factura", ""))
    autoriza_nombre = str(form.get("autoriza_input", ""))
    autoriza_email = str(form.get("autoriza_email", ""))
    
    # ✅ NUEVO: Extraer números de factura únicos de las guías (documentos)
    # Las guías contienen los números de factura/documento
    facturas_unicas = []
    for guia in guias:
        if guia and guia.strip() and guia.strip() != "SIN_DOCUMENTO":
            if guia.strip() not in facturas_unicas:
                facturas_unicas.append(guia.strip())
    
    # Unir con comas o usar "---" si no hay facturas
    numero_factura = ", ".join(facturas_unicas) if facturas_unicas else "---"
    current_app.logger.info(f"📄 Números de factura detectados: {numero_factura}")
    
    condicion_pago = str(form.get("condicion_pago", "---"))
    proyecto = str(form.get("proyecto", "---"))
    
    total_neto = safe_float(form.get("total_neto", "0"))
    total_iva = safe_float(form.get("total_iva", "0"))
    total_pagar = safe_float(form.get("total_pagar", "0"))
    
    # OC principal (primera de la lista)
    oc_principal = ocs[0] if ocs else "---"
    
    # Datos del proveedor desde Supabase
    proveedor_data = {
        "nombre": nombre_proveedor,
        "paguese_a": "",
        "rut": "",
        "cuenta": "",
        "banco": "",
        "correo": ""
    }
    
    if supabase and nombre_proveedor:
        try:
            prov_rows = (
                supabase.table("proveedores")
                .select("paguese_a, rut, cuenta, banco, correo")
                .eq("nombre", nombre_proveedor)
                .limit(1)
                .execute()
                .data or []
            )
            if prov_rows:
                prov = prov_rows[0]
                proveedor_data.update({
                    "paguese_a": str(prov.get("paguese_a", "")),
                    "rut": str(prov.get("rut", "")),
                    "cuenta": str(prov.get("cuenta", "")),
                    "banco": str(prov.get("banco", "")),
                    "correo": str(prov.get("correo", "")),
                })
        except Exception as e:
            current_app.logger.warning(f"No se pudieron cargar datos del proveedor: {e}")
    
    # Si tenemos OC, intentar obtener datos adicionales
    if supabase and oc_principal and oc_principal != "---":
        try:
            oc_data = (
                supabase.table("orden_de_compra")
                .select("proyecto, condicion_de_pago")
                .eq("orden_compra", oc_principal)
                .limit(1)
                .execute()
                .data or []
            )
            if oc_data:
                proyecto_id = oc_data[0].get("proyecto")
                
                # Obtener nombre del proyecto si tenemos ID
                if proyecto_id:
                    try:
                        proy_data = (
                            supabase.table("proyectos")
                            .select("proyecto")
                            .eq("id", proyecto_id)
                            .limit(1)
                            .execute()
                            .data or []
                        )
                        if proy_data:
                            proyecto = str(proy_data[0].get("proyecto", "---"))
                        else:
                            proyecto = str(proyecto_id)  # Fallback al ID si no se encuentra
                    except Exception as e2:
                        current_app.logger.warning(f"No se pudo obtener nombre del proyecto: {e2}")
                        proyecto = str(proyecto_id)
                
                if not condicion_pago or condicion_pago == "---":
                    condicion_pago = str(oc_data[0].get("condicion_de_pago", "---"))
        except Exception as e:
            current_app.logger.warning(f"No se pudieron cargar datos de la OC: {e}")
    
    # Preparar datos para el PDF
    datos_orden = {
        "numero_op": numero,
        "fecha": datetime.now().strftime('%d-%m-%Y'),
        "fecha_factura": fecha_factura,
        "fecha_vencimiento": fecha_venc,
        "numero_factura": numero_factura,
        "oc_principal": oc_principal,
        "condicion_pago": condicion_pago,
        "proyecto": proyecto,
        "empresa": {
            "nombre": "SOMYL S.A.",
            "rut": "76.002.581-K",
            "rubro": "TELECOMUNICACIONES",
            "direccion": "PUERTA ORIENTE 361 OF 311 B TORRE B COLINA",
            "telefono": "232642974"
        },
        "proveedor": proveedor_data,
        "detalle_compra": detalle_op,
        "autorizador": {
            "nombre": autoriza_nombre,
            "correo": autoriza_email
        },
        "lineas": [
            {
                "oc": oc,
                "guia": guia,
                "descripcion": desc
            }
            for oc, guia, desc in zip(ocs, guias, descripciones)
        ],
        "total_neto": total_neto,
        "total_iva": total_iva,
        "total_pagar": total_pagar
    }
    
    # Generar el PDF
    filepath = _generar_pdf_orden_pago(datos_orden)
    
    # Leer el archivo generado
    with open(filepath, 'rb') as f:
        pdf_bytes = f.read()
    
    filename = os.path.basename(filepath)
    
    return pdf_bytes, filename


def _generar_pdf_orden_pago(datos_orden):
    """
    Genera el PDF de Orden de Pago usando ReportLab.
    Similar a generar_pdf_orden_compra pero adaptado para órdenes de pago.
    
    Args:
        datos_orden: Dict con los datos de la orden
    
    Returns:
        str: Ruta del archivo PDF generado
    """
    # Crear directorio para PDFs
    pdf_dir = os.path.join(os.path.dirname(__file__), '..', 'pdfs_generados', 'ordenes_pago')
    os.makedirs(pdf_dir, exist_ok=True)
    
    # Nombre del archivo con número de OP y nombre del proveedor
    numero_op = str(datos_orden.get('numero_op', 'SIN_NUMERO'))
    proveedor_nombre = str(datos_orden.get('proveedor', {}).get('nombre', 'SIN_PROVEEDOR'))
    # Limpiar nombre del proveedor para nombre de archivo (quitar espacios y caracteres especiales)
    proveedor_clean = proveedor_nombre.replace(' ', '_').replace('.', '').replace(',', '').upper()
    filename = f"orden_pago_{numero_op}_{proveedor_clean}.pdf"
    filepath = os.path.join(pdf_dir, filename)
    
    # Configurar documento
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=25*mm
    )
    
    elements = []
    
    # --- ESTILOS ---
    styles = getSampleStyleSheet()
    
    # Colores más sutiles (estilo del HTML template)
    COLOR_BORDER = colors.HexColor('#444444')
    COLOR_HEADER_BG = colors.HexColor('#f0f0f0')
    COLOR_TEXT = colors.black
    COLOR_GRAY = colors.HexColor('#555555')
    
    styles.add(ParagraphStyle(
        name='RightSmall',
        parent=styles['Normal'],
        alignment=TA_RIGHT,
        fontSize=10,
        textColor=COLOR_TEXT,
        leading=12
    ))
    
    styles.add(ParagraphStyle(
        name='Small',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_TEXT,
        leading=12
    ))
    
    styles.add(ParagraphStyle(
        name='Tiny',
        parent=styles['Normal'],
        fontSize=9,
        textColor=COLOR_GRAY,
        leading=11,
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        name='CompanyName',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=COLOR_TEXT,
        spaceAfter=3,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=COLOR_TEXT,
        fontName='Helvetica-Bold',
        spaceAfter=4
    ))
    
    styles.add(ParagraphStyle(
        name='SectionLabel',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_TEXT,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='DetailText',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_TEXT,
        leading=13
    ))
    
    # --- TÍTULO PRINCIPAL (centrado como el HTML) ---
    empresa = datos_orden.get('empresa', {})
    empresa_nombre = str(empresa.get('nombre', 'SOMYL S.A.'))
    empresa_rut = str(empresa.get('rut', '76.002.581-K'))
    empresa_rubro = str(empresa.get('rubro', 'TELECOMUNICACIONES'))
    empresa_direccion = str(empresa.get('direccion', 'PUERTA ORIENTE 361 OF 311 B TORRE B COLINA'))
    empresa_telefono = str(empresa.get('telefono', '232642974'))
    
    elements.append(Paragraph(f"<b>Orden de Pago #{numero_op}</b>", styles['CompanyName']))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(
        f"<b>{empresa_nombre}</b><br/>"
        f"RUT: {empresa_rut} &nbsp; Teléfono: {empresa_telefono}<br/>"
        f"Rubro: {empresa_rubro}<br/>"
        f"Dirección: {empresa_direccion}",
        styles['Tiny']
    ))
    elements.append(Spacer(1, 8*mm))
    
    # --- SECCIÓN DE 2 COLUMNAS (Páguese a | Detalles de Compra) ---
    proveedor = datos_orden.get('proveedor', {})
    
    # Columna 1: Páguese a
    datos_col1 = [
        [Paragraph('<b>Páguese a:</b>', styles['SectionTitle'])],
        [Paragraph(f"<b>{str(proveedor.get('paguese_a', proveedor.get('nombre', 'N/A')))}</b>", styles['DetailText'])],
        [Paragraph(f"<b>Nombre:</b> {str(proveedor.get('nombre', 'N/A'))}", styles['Small'])],
        [Paragraph(f"<b>RUT:</b> {str(proveedor.get('rut', 'N/A'))}", styles['Small'])],
        [Paragraph(f"<b>Cuenta Corriente:</b> {str(proveedor.get('cuenta', '---'))}", styles['Small'])],
        [Paragraph(f"<b>Banco:</b> {str(proveedor.get('banco', '---'))}", styles['Small'])],
        [Paragraph(f"<b>Correo:</b> {str(proveedor.get('correo', '---'))}", styles['Small'])],
        [Spacer(1, 2*mm)],
        [Paragraph('<b>Detalle de O.P.:</b>', styles['SectionTitle'])],
        [Paragraph(str(datos_orden.get('detalle_compra', '---')), styles['Small'])]
    ]
    
    tabla_col1 = Table(datos_col1, colWidths=[doc.width*0.48])
    tabla_col1.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3)
    ]))
    
    # Columna 2: Detalles de Compra
    datos_col2 = [
        [Paragraph('<b>Detalles de Compra</b>', styles['SectionTitle'])],
        [Paragraph(f"<b>Número de Factura:</b> {str(datos_orden.get('numero_factura', '---'))}", styles['Small'])],
        [Paragraph(f"<b>OC:</b> {str(datos_orden.get('oc_principal', '---'))}", styles['Small'])],
        [Paragraph(f"<b>Condición de Pago:</b> {str(datos_orden.get('condicion_pago', '---'))}", styles['Small'])],
        [Paragraph(f"<b>Fecha Factura:</b> {str(datos_orden.get('fecha_factura', '---'))}", styles['Small'])],
        [Paragraph(f"<b>Fecha de Vencimiento:</b> {str(datos_orden.get('fecha_vencimiento', '---'))}", styles['Small'])],
        [Paragraph(f"<b>Proyecto:</b> {str(datos_orden.get('proyecto', '---'))}", styles['Small'])]
    ]
    
    tabla_col2 = Table(datos_col2, colWidths=[doc.width*0.48])
    tabla_col2.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3)
    ]))
    
    # Combinar las 2 columnas
    tabla_superior = Table(
        [[tabla_col1, tabla_col2]], 
        colWidths=[doc.width*0.50, doc.width*0.50]
    )
    tabla_superior.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0)
    ]))
    elements.append(tabla_superior)
    elements.append(Spacer(1, 6*mm))
    
    # --- TABLA DE DETALLE DE MATERIALES (como el HTML template) ---
    lineas = datos_orden.get('lineas', [])
    
    # Encabezado de la tabla
    datos_lineas = [[
        Paragraph('<b>Guía Recepción</b>', styles['SectionLabel']),
        Paragraph('<b>Orden Compra</b>', styles['SectionLabel']),
        Paragraph('<b>Descripción</b>', styles['SectionLabel'])
    ]]
    
    # Filas de datos
    for linea in lineas:
        datos_lineas.append([
            Paragraph(str(linea.get('guia', '')), styles['Small']),
            Paragraph(str(linea.get('oc', '')), styles['Small']),
            Paragraph(str(linea.get('descripcion', '')), styles['Small'])
        ])
    
    # Anchos de columna (como en el HTML: 80px, 60px, resto)
    col_widths = [30*mm, 25*mm, doc.width - 55*mm]
    tabla_lineas = Table(datos_lineas, colWidths=col_widths, repeatRows=1)
    tabla_lineas.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_HEADER_BG),
        ('TEXTCOLOR', (0,0), (-1,-1), COLOR_TEXT),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 1, COLOR_BORDER),
        ('LINEBELOW', (0,0), (-1,0), 1, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,1), (1,-1), 'LEFT'),
        ('ALIGN', (2,1), (2,-1), 'LEFT'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5)
    ]))
    
    elements.append(Paragraph('<b>Detalle de Material</b>', styles['SectionTitle']))
    elements.append(Spacer(1, 3*mm))
    elements.append(tabla_lineas)
    elements.append(Spacer(1, 8*mm))
    
    # --- TOTALES (alineados a la derecha, como el HTML) ---
    total_neto = datos_orden.get('total_neto', 0)
    total_iva = datos_orden.get('total_iva', 0)
    total_pagar = datos_orden.get('total_pagar', 0)
    
    # Tabla de totales (40% del ancho, flotando a la derecha)
    datos_totales = [
        [Paragraph('<b>Total Neto:</b>', styles['Small']), 
         Paragraph(f'<b>{fmt_money(total_neto)}</b>', styles['RightSmall'])],
        [Paragraph('<b>Total IVA (19%):</b>', styles['Small']), 
         Paragraph(f'<b>{fmt_money(total_iva)}</b>', styles['RightSmall'])],
        [Paragraph('<b>Total a Pagar:</b>', styles['Small']), 
         Paragraph(f'<b>{fmt_money(total_pagar)}</b>', styles['RightSmall'])]
    ]
    
    # Crear tabla con espacio vacío a la izquierda (60%) y totales a la derecha (40%)
    tabla_totales_container = Table(
        [['', Table(datos_totales, colWidths=[35*mm, 35*mm])]],
        colWidths=[doc.width*0.6, doc.width*0.4]
    )
    tabla_totales_container.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0)
    ]))
    
    # Aplicar estilo a la tabla interna de totales
    tabla_totales_interna = tabla_totales_container._cellvalues[0][1]
    tabla_totales_interna.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, COLOR_BORDER),
        ('ALIGN', (0,0), (0,-1), 'RIGHT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('BACKGROUND', (0,0), (-1,-1), colors.white)
    ]))
    
    elements.append(tabla_totales_container)
    elements.append(Spacer(1, 3*mm))
    
    # Línea de separación
    elements.append(Spacer(1, 10*mm))
    
    # --- AUTORIZACIÓN (como el HTML) ---
    autorizador = datos_orden.get('autorizador', {})
    autoriza_nombre = str(autorizador.get('nombre', ''))
    
    if autoriza_nombre:
        elements.append(Paragraph(f'<b>Autorizado por:</b>', styles['SectionTitle']))
        elements.append(Spacer(1, 1*mm))
        elements.append(Paragraph(f'<b>{autoriza_nombre}</b>', styles['Small']))
    
    # --- PIE DE PÁGINA (como el HTML) ---
    elements.append(Spacer(1, 15*mm))
    elements.append(Paragraph(
        f'{empresa_nombre} — Orden de Pago<br/>'
        f'Fecha de emisión: {datos_orden.get("fecha", "")}',
        styles['Tiny']
    ))
    
    # Construir PDF
    doc.build(elements)
    
    return filepath


def generar_pdf_por_numero(orden_numero):
    """
    Genera PDF consultando la BD por número de orden.
    
    Args:
        orden_numero: Número de la orden de pago
    
    Returns:
        tuple: (pdf_bytes, filename)
    """
    supabase = current_app.config.get("SUPABASE")
    if not supabase:
        raise RuntimeError("Supabase client not configured")
    
    # Consultar líneas de la orden
    try:
        lineas = (
            supabase.table("orden_de_pago")
            .select("*")
            .eq("orden_numero", orden_numero)
            .execute()
            .data or []
        )
    except Exception as e:
        current_app.logger.error(f"Error consultando orden {orden_numero}: {e}")
        raise RuntimeError(f"Error consultando la base de datos: {str(e)}")
    
    if not lineas:
        raise ValueError(f"Orden {orden_numero} no encontrada")
    
    # Extraer datos de las líneas
    ocs = [str(l.get("orden_compra") or "") for l in lineas]
    guias = [str(l.get("doc_recep") or "") for l in lineas]
    descripciones = [str(l.get("material_nombre") or "") for l in lineas]
    
    # Tomar datos de la primera línea
    primera = lineas[0]
    
    # Calcular totales si no vienen en los datos
    total_neto = safe_float(primera.get("neto_total_recibido", 0))
    total_iva = safe_float(primera.get("total_iva", 0))
    total_pagar = safe_float(primera.get("costo_final_con_iva", 0))
    
    # Si no hay totales precalculados, sumar desde las líneas
    if total_pagar == 0:
        for linea in lineas:
            total_pagar += safe_float(linea.get("costo_final_con_iva", 0))
    
    if total_neto == 0:
        for linea in lineas:
            total_neto += safe_float(linea.get("neto_total_recibido", 0))
    
    # Calcular IVA
    total_iva = total_pagar - total_neto
    
    # Construir form-like dict con todos los campos necesarios
    form_like = {
        "orden_compra[]": ocs,
        "guia_recepcion[]": guias,
        "descripcion[]": descripciones,
        "next_num": orden_numero,
        "nombre_proveedor": str(primera.get("proveedor_nombre", "")),
        "detalle_compra": str(primera.get("detalle_compra", "")),
        "vencimiento": str(primera.get("vencimiento", "")),
        "fecha_factura": str(primera.get("fecha_factura", "")),
        "autoriza_input": str(primera.get("autoriza_nombre", "")),
        "autoriza_email": str(primera.get("autoriza_email", "")),
        "numero_factura": str(primera.get("factura", "---")),
        "condicion_pago": str(primera.get("condicion_pago", "---")),
        "proyecto": str(primera.get("proyecto", "---")),
        "total_neto": total_neto,
        "total_iva": total_iva,
        "total_pagar": total_pagar
    }
    
    return generar_pdf_from_form(form_like)
