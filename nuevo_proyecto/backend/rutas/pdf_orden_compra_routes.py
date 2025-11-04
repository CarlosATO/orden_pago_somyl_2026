"""
Rutas para generación de PDF de Órdenes de Compra
"""
from flask import Blueprint, request, jsonify, send_file, current_app
from backend.utils.decorators import token_required
from backend.pdf.pdf_orden_compra import generar_pdf_orden_compra
from backend.pdf.ordenes_pago_pdf import generar_pdf_por_numero, generar_pdf_from_form
import os

pdf_oc_bp = Blueprint('pdf_orden_compra', __name__)

@pdf_oc_bp.route('/generar-pdf-orden-compra', methods=['POST'])
@token_required
def generar_pdf_oc(current_user):
    """
    Endpoint para generar PDF de Orden de Compra
    Recibe los datos de la orden y retorna el PDF
    """
    try:
        datos = request.get_json()
        
        if not datos:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        # Generar el PDF
        ruta_pdf = generar_pdf_orden_compra(datos)
        
        # Verificar que el archivo existe
        if not os.path.exists(ruta_pdf):
            return jsonify({'error': 'Error al generar el PDF'}), 500
        
        # Enviar el archivo como descarga
        numero_oc = datos.get('numero_oc', 'SIN_NUMERO')
        return send_file(
            ruta_pdf,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'OrdenCompra_{numero_oc}.pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error al generar PDF: {str(e)}")
        return jsonify({'error': f'Error al generar PDF: {str(e)}'}), 500


@pdf_oc_bp.route('/ordenes_pago/pdf/<int:orden_numero>', methods=['GET'])
@token_required
def generar_pdf_orden_pago_route(current_user, orden_numero):
    """
    Genera y devuelve el PDF de una Orden de Pago por su número.
    """
    try:
        pdf_bytes, filename = generar_pdf_por_numero(orden_numero)
        if not pdf_bytes:
            return jsonify({'error': 'Error al generar PDF'}), 500

        # Devolver como attachment
        from flask import make_response
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except ValueError as ve:
        return jsonify({'error': str(ve)}), 404
    except Exception as e:
        current_app.logger.exception(f"Error en generar_pdf_orden_pago_route: {e}")
        return jsonify({'error': f'Error al generar PDF: {str(e)}'}), 500


@pdf_oc_bp.route('/ordenes_pago/generar-pdf', methods=['POST'])
@token_required
def generar_pdf_orden_pago_from_form(current_user):
    """
    Genera y devuelve el PDF de una Orden de Pago a partir de los datos enviados en el body (JSON).
    Esto permite generar un PDF para una orden en modo creación sin persistirla.
    """
    try:
        datos = request.get_json()
        if not datos:
            return jsonify({'error': 'No se recibieron datos para generar el PDF'}), 400

        pdf_bytes, filename = generar_pdf_from_form(datos)

        if not pdf_bytes:
            return jsonify({'error': 'Error al generar el PDF'}), 500

        from flask import make_response
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        current_app.logger.exception(f"Error en generar_pdf_orden_pago_from_form: {e}")
        return jsonify({'error': f'Error al generar PDF: {str(e)}'}), 500
