from flask import Blueprint, request, current_app, render_template, make_response
from datetime import date
import pdfkit

bp_pdf = Blueprint(
    'ordenes_pago_pdf',
    __name__,
    template_folder='../templates/ordenes_pago'
)

def safe_float(value, default=0.0):
    """Convierte un valor a float de manera segura, retornando default si está vacío o es inválido"""
    if not value or value.strip() == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Convierte un valor a int de manera segura, retornando default si está vacío o es inválido"""
    if not value or str(value).strip() == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

@bp_pdf.route('/ordenes_pago/pdf', methods=['POST'], endpoint='pdf')
def generar_pdf():

    supabase = current_app.config['SUPABASE']
    # Listas de detalle (ya vienen filtradas y sin duplicados desde el JS)
    ocs           = request.form.getlist('orden_compra[]')
    guias         = request.form.getlist('guia_recepcion[]')
    descripciones = request.form.getlist('descripcion[]')

    # --- Obtener nombres de proyectos asociados a las OCs ---
    proyecto_ids = set()
    if ocs:
        oc_numbers = [int(oc) for oc in ocs if str(oc).isdigit()]
        # Paginación manual para orden_de_compra
        page_size = 1000
        offset = 0
        while True:
            batch = (
                supabase.table('orden_de_compra')
                    .select('orden_compra, proyecto')
                    .in_('orden_compra', oc_numbers)
                    .range(offset, offset + page_size - 1)
                    .execute()
                    .data or []
            )
            for row in batch:
                pid = row.get('proyecto')
                if pid:
                    proyecto_ids.add(pid)
            if len(batch) < page_size:
                break
            offset += page_size

    # Buscar nombres de proyectos en tabla proyectos
    proyectos_nombres = set()
    if proyecto_ids:
        page_size = 1000
        offset = 0
        ids_list = list(proyecto_ids)
        while True:
            batch = (
                supabase.table('proyectos')
                    .select('id, proyecto')
                    .in_('id', ids_list)
                    .range(offset, offset + page_size - 1)
                    .execute()
                    .data or []
            )
            for row in batch:
                nombre = row.get('proyecto')
                if nombre:
                    proyectos_nombres.add(nombre)
            if len(batch) < page_size:
                break
            offset += page_size
    if not proyectos_nombres:
        proyectos_nombres = {'Sin proyecto'}
    proyectos_str = ' - '.join(sorted(proyectos_nombres, key=lambda x: x.lower()))
    f = request.form

    # 1) Lectura de datos del formulario
    numero           = safe_int(f.get('next_num', '0'))
    nombre_proveedor = f.get('nombre_proveedor', '')
    detalle_op       = f.get('detalle_compra', '')
    fecha_venc       = f.get('vencimiento', '')
    fecha_factura    = f.get('fecha_factura', '')
    autoriza_nombre  = f.get('autoriza_input', '')
    autoriza_email   = f.get('autoriza_email', '')

    # Totales (verificar si son sin IVA consultando las órdenes de compra originales)
    total_neto  = safe_float(f.get('total_neto', '0'))
    total_iva   = safe_float(f.get('total_iva', '0'))
    total_pagar = safe_float(f.get('total_pagar', '0'))

    # Verificar si las órdenes de compra originales son sin IVA
    sin_iva = False
    if ocs:
        try:
            # Convertir OCs a enteros y verificar si alguna es sin IVA
            oc_numbers = []
            for oc in ocs:
                try:
                    oc_numbers.append(int(oc))
                except (ValueError, TypeError):
                    continue
            if oc_numbers:
                # Consultar las órdenes de compra para verificar fac_sin_iva
                oc_rows = (
                    supabase.table('orden_de_compra')
                            .select('fac_sin_iva')
                            .in_('orden_compra', oc_numbers)
                            .execute()
                            .data
                ) or []
                # Si alguna orden de compra es sin IVA, toda la orden de pago es sin IVA
                for oc_row in oc_rows:
                    if oc_row.get('fac_sin_iva', 0):
                        sin_iva = True
                        break
        except Exception as e:
            current_app.logger.error(f"Error verificando IVA: {e}")
            sin_iva = False

    # Recalcular IVA y total a pagar según si es sin IVA
    if sin_iva:
        total_iva = 0
        total_pagar = total_neto
    else:
        # Solo recalcular si el IVA no fue proporcionado correctamente
        if total_iva == 0 and total_neto > 0:
            total_iva = round(total_neto * 0.19)
            total_pagar = total_neto + total_iva

    # 2) Información fija de la empresa
    empresa = {
        'nombre': 'Somyl S.A.',
        'rut': '76.002.581-K',
        'rubro': 'TELECOMUNICACIONES',
        'direccion': 'PUERTA ORIENTE 361 OF 311 B TORRE B COLINA',
        'telefono': '232642974'
    }

    # 3) Datos del proveedor
    prov_rows = (
        supabase.table('proveedores')
                .select('paguese_a, rut, cuenta, banco, correo')
                .eq('nombre', nombre_proveedor)
                .limit(1)
                .execute()
                .data
    ) or []

    prov = prov_rows[0] if prov_rows else {}
    proveedor = {
        'paguese_a': prov.get('paguese_a', ''),
        'nombre':     nombre_proveedor,
        'rut':        prov.get('rut', ''),
        'cuenta':     prov.get('cuenta', ''),
        'banco':      prov.get('banco', ''),
        'correo':     prov.get('correo', '')
    }

    # 4) Condición de pago (tomamos la primera OC de la lista)
    cond_pago = ''
    if ocs and len(ocs) > 0:
        oc0 = safe_int(ocs[0])
        if oc0 > 0:
            oc_rows = (
                supabase.table('orden_de_compra')
                        .select('condicion_de_pago')
                        .eq('orden_compra', oc0)
                        .limit(1)
                        .execute()
                        .data
            ) or []
            if oc_rows:
                cond_pago = oc_rows[0].get('condicion_de_pago', '')

    # 5) Preparar detalle de materiales
    detalle_material = []
    for guia, oc, desc in zip(guias, ocs, descripciones):
        detalle_material.append({
            'guia': guia,
            'oc': oc,
            'descripcion': desc
        })

    # 6) Autoriza
    autorizador = {
        'nombre': autoriza_nombre,
        'correo': autoriza_email
    }

    # 7) Contexto para la plantilla
    contexto = {
        'empresa': empresa,
        'proveedor': proveedor,
        'numero': numero,
        'facturas': guias,
        'ocs': ocs,
        'cond_pago': cond_pago,
        'fecha_venc': fecha_venc,
        'fecha_factura': fecha_factura,
        'detalle_op': detalle_op,
        'detalle_material': detalle_material,
        'total_neto': total_neto,
        'total_iva': total_iva,
        'total_pagar': total_pagar,
        'sin_iva': sin_iva,  # Agregar información de si es sin IVA
        'autorizador': autorizador,
        'fecha_emision': date.today().isoformat(),
        'proyectos_str': proyectos_str
    }

    # 8) Renderizar HTML y generar PDF
    html = render_template('ordenes_pago/pdf_template.html', **contexto)

    try:
        # Intentar diferentes configuraciones de wkhtmltopdf para producción
        config = None
        
        # 1. Intentar con la instalación del sistema (Railway, Heroku, etc.)
        try:
            import subprocess
            result = subprocess.run(['which', 'wkhtmltopdf'], capture_output=True, text=True)
            if result.returncode == 0:
                wkhtmltopdf_path = result.stdout.strip()
                current_app.logger.info(f"wkhtmltopdf encontrado en: {wkhtmltopdf_path}")
                config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        except Exception as e:
            current_app.logger.warning(f"Error buscando wkhtmltopdf: {e}")
        
        # 2. Fallback a rutas comunes si no se encuentra
        if not config:
            common_paths = [
                '/usr/bin/wkhtmltopdf',
                '/usr/local/bin/wkhtmltopdf',
                '/bin/wkhtmltopdf',
                'wkhtmltopdf'  # Usar PATH del sistema
            ]
            
            for path in common_paths:
                try:
                    config = pdfkit.configuration(wkhtmltopdf=path)
                    # Probar si la configuración funciona
                    pdfkit.from_string('<html><body>Test</body></html>', False, configuration=config)
                    current_app.logger.info(f"wkhtmltopdf configurado exitosamente en: {path}")
                    break
                except Exception as e:
                    current_app.logger.warning(f"Ruta {path} no funciona: {e}")
                    continue
        
        # 3. Si no se encuentra wkhtmltopdf, usar configuración sin path (usar PATH del sistema)
        if not config:
            current_app.logger.info("Usando configuración por defecto de wkhtmltopdf")
            config = None
        
        # Opciones para el PDF
        options = {
            'enable-local-file-access': None,
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None
        }
        
        # Generar PDF con manejo de errores
        if config:
            pdf_bytes = pdfkit.from_string(html, False, configuration=config, options=options)
        else:
            pdf_bytes = pdfkit.from_string(html, False, options=options)
            
        current_app.logger.info(f"PDF generado exitosamente para orden {numero}")
        
        # Almacenar el PDF para futuro envío por correo
        import os
        pdf_dir = os.path.join(current_app.root_path, 'static', 'ordenes_pago', 'generated_pdfs')
        os.makedirs(pdf_dir, exist_ok=True)
        
        safe_name = proveedor.get('paguese_a', '').replace(' ', '_')
        pdf_filename = f"orden_pago_{numero}_{safe_name}.pdf"
        pdf_filepath = os.path.join(pdf_dir, pdf_filename)
        
        with open(pdf_filepath, 'wb') as f:
            f.write(pdf_bytes)
        current_app.logger.info(f"PDF almacenado en: {pdf_filepath}")
        
    except Exception as e:
        current_app.logger.error(f"Error generando PDF: {e}")
        # Fallback: devolver el HTML como respuesta de error
        from flask import jsonify
        return jsonify({
            'error': 'Error generando PDF',
            'message': str(e),
            'suggestion': 'Contacte al administrador del sistema'
        }), 500

    # 9) Devolver PDF como descarga
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    # Build a safe filename including the beneficiary name
    safe_name = proveedor.get('paguese_a', '').replace(' ', '_')
    filename = f"orden_pago_{numero}_{safe_name}.PDF"
    response.headers['Content-Disposition'] = f'attachment; filename=\"{filename}\"'
    return response