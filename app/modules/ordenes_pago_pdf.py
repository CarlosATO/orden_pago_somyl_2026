from flask import Blueprint, request, current_app, render_template, make_response
from datetime import date
import pdfkit
from flask_mail import Message
import pdfkit
from flask import render_template

bp_pdf = Blueprint(
    'ordenes_pago_pdf',
    __name__,
    template_folder='../templates/ordenes_pago'
)

@bp_pdf.route('/ordenes_pago/pdf', methods=['POST'], endpoint='pdf')
def generar_pdf():
    supabase = current_app.config['SUPABASE']
    f = request.form

    # 1) Lectura de datos del formulario
    numero           = int(f['next_num'])
    nombre_proveedor = f['nombre_proveedor']
    detalle_op       = f.get('detalle_compra', '')
    fecha_venc       = f.get('vencimiento')
    fecha_factura    = f.get('fecha_factura')
    autoriza_nombre  = f.get('autoriza_input', '')
    autoriza_email   = f.get('autoriza_email', '')

    # Listas de detalle (ya vienen filtradas y sin duplicados desde el JS)
    ocs           = f.getlist('orden_compra[]')
    guias         = f.getlist('guia_recepcion[]')
    descripciones = f.getlist('descripcion[]')

    # Totales
    total_neto  = float(f['total_neto'])
    total_iva   = float(f['total_iva'])
    total_pagar = float(f['total_pagar'])

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
    if ocs:
        oc0 = int(ocs[0])
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
        'autorizador': autorizador,
        'fecha_emision': date.today().isoformat()
    }

    # 8) Renderizar HTML y generar PDF
    html = render_template('ordenes_pago/pdf_template.html', **contexto)

    # Asegúrate de que wkhtmltopdf esté en /usr/local/bin o ajusta la ruta
    config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf')
    options = {
        'enable-local-file-access': None
    }
    pdf_bytes = pdfkit.from_string(html, False, configuration=config, options=options)

    # 9) Devolver PDF como descarga
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    # Build a safe filename including the beneficiary name
    safe_name = proveedor.get('paguese_a', '').replace(' ', '_')
    filename = f"orden_pago_{numero}_{safe_name}.PDF"
    response.headers['Content-Disposition'] = f'attachment; filename=\"{filename}\"'
    return response