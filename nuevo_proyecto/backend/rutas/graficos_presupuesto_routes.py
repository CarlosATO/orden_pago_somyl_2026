"""
Rutas para datos de gráficos de comparación Presupuesto vs Actual
Devuelve un JSON con valores agregados para las barras solicitadas.
"""
from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required
# Reuse production retrieval from estado_presupuesto to keep values consistent
from backend.modules.estado_presupuesto import get_produccion_actual_nhost
import logging

bp = Blueprint('graficos_presupuesto', __name__)
logger = logging.getLogger(__name__)


@bp.route('/graficos-presupuesto', methods=['GET'])
@token_required
def graficos_presupuesto(current_user):
    """Devuelve datos resumidos para los gráficos:
    - venta_presupuestada vs produccion_actual
    - gasto_presupuestado vs gasto_actual
    - saldos: saldo_presupuestado vs saldo_actual

    Opcional: ?proyecto_id=<id> para filtrar por proyecto
    """
    supabase = current_app.config.get('SUPABASE')
    if not supabase:
        logger.error('Supabase client no configurado')
        return jsonify({"success": False, "message": "Error de configuración del servidor"}), 500

    proyecto_filter = request.args.get('proyecto_id')

    try:
        # Obtener proyectos (aplica filtro si se indica)
        query = supabase.table('proyectos').select('id, venta')
        if proyecto_filter and proyecto_filter != 'todos':
            try:
                query = query.eq('id', int(proyecto_filter))
            except:
                pass

        res_proy = query.execute()
        proyectos = res_proy.data if res_proy and hasattr(res_proy, 'data') else []

        proyecto_ids = [p['id'] for p in proyectos]

        # Sumar venta presupuestada
        venta_total = 0
        for p in proyectos:
            try:
                venta_total += int(p.get('venta') or 0)
            except:
                pass

        # Obtener monto presupuesto total (presupuesto table)
        presupuesto_total = 0
        if proyecto_ids:
            res_pres = (
                supabase.table('presupuesto')
                .select('monto')
                .in_('proyecto_id', proyecto_ids)
                .execute()
            )
            pres_rows = res_pres.data if res_pres and hasattr(res_pres, 'data') else []
            for pr in pres_rows:
                try:
                    presupuesto_total += float(pr.get('monto') or 0)
                except:
                    pass

        # Obtener gasto real (orden_de_pago.costo_final_con_iva) filtrado por proyecto
        gasto_real_total = 0
        if proyecto_ids:
            res_ops = (
                supabase.table('orden_de_pago')
                .select('costo_final_con_iva')
                .in_('proyecto', proyecto_ids)
                .execute()
            )
            ops = res_ops.data if res_ops and hasattr(res_ops, 'data') else []
            for op in ops:
                try:
                    gasto_real_total += float(op.get('costo_final_con_iva') or 0)
                except:
                    pass

            # Gastos directos también
            res_gd = (
                supabase.table('gastos_directos')
                .select('monto')
                .in_('proyecto_id', proyecto_ids)
                .execute()
            )
            gds = res_gd.data if res_gd and hasattr(res_gd, 'data') else []
            for gd in gds:
                try:
                    gasto_real_total += float(gd.get('monto') or 0)
                except:
                    pass

        # Para producción actual consultamos Nhost (misma fuente que el endpoint
        # /api/estado-presupuesto) para mantener los valores idénticos.
        produccion_total = 0
        for p in proyectos:
            proyecto_id = p.get('id')
            try:
                produccion_nhost = get_produccion_actual_nhost(proyecto_id)
                produccion_total += float(produccion_nhost or 0)
            except Exception:
                # Si falla, no detener el proceso; sumar 0
                pass

        # Calcular saldos
        saldo_presupuestado = venta_total - int(presupuesto_total)
        saldo_actual = produccion_total - int(gasto_real_total)

        payload = {
            'venta_presupuestada': int(venta_total),
            'produccion_actual': int(produccion_total),
            'gasto_presupuestado': int(presupuesto_total),
            'gasto_actual': int(gasto_real_total),
            'saldo_presupuestado': int(saldo_presupuestado),
            'saldo_actual': int(saldo_actual)
        }

        return jsonify({"success": True, "data": payload})

    except Exception as e:
        logger.exception('Error generando datos de graficos')
        return jsonify({"success": False, "message": str(e)}), 500
