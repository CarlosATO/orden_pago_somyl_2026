"""
Rutas para generación de PDF de Órdenes de Compra
"""
from flask import Blueprint, request, jsonify, send_file, current_app
from backend.utils.decorators import token_required
from backend.pdf.pdf_orden_compra import generar_pdf_orden_compra
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
