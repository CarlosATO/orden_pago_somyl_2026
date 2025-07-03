# app/modules/ordenes_pago_create.py

from flask import Blueprint, request, current_app, flash, redirect, url_for
from datetime import date

bp_create = Blueprint('ordenes_pago_create', __name__)


@bp_create.route('/ordenes_pago/create', methods=['POST'], endpoint='create')
def crear_orden_pago():
    supabase = current_app.config['SUPABASE']
    f = request.form

    # 1) Datos generales
    numero            = int(f['next_num'])
    nombre_proveedor  = f['nombre_proveedor']
    proveedor_id      = int(f['proveedor_id'])
    autoriza_id       = int(f['autoriza_id'])
    fecha_factura     = f['fecha_factura']
    fecha_vencimiento = f['fecha_vencimiento']
    estado_pago       = f.get('estado_pago', '')
    detalle_op        = f.get('detalle_op', '')

    # Fecha de creación (columna 'fecha')
    hoy = date.today().isoformat()

    # 2) Listas de detalle (todas vienen en paralelo)
    oc_list         = f.getlist('orden_compra[]')    # ej: ["7", "7", ...]
    guias           = f.getlist('guia_recepcion[]')  # ej: ["10", "10", ...]
    arts            = f.getlist('art_corr[]')        # ej: ["11", "12", ...]
    descripciones   = f.getlist('descripcion[]')
    recepciones     = f.getlist('recepcion[]')
    netos_unitarios = f.getlist('neto_unitario[]')
    totales_netos   = f.getlist('neto_total[]')

    # 3) Próximo n_ingreso en la tabla orden_de_pago (no confundir con orden_compra)
    resp = supabase.table('orden_de_pago') \
                   .select('n_ingreso') \
                   .order('n_ingreso', desc=True) \
                   .limit(1) \
                   .execute().data or []
    max_n = resp[0]['n_ingreso'] if resp else 0
    n_ingreso_next = max_n + 1

    # 4) Construir payload línea a línea
    payload = []
    for oc_numero, guia, art_corr, desc, cant, nu, tn in zip(
        oc_list, guias, arts, descripciones, recepciones, netos_unitarios, totales_netos
    ):
        # 4.0) Convertir a tipos adecuados:
        oc_int     = int(oc_numero)
        art_corr_i = int(art_corr)
        cant_i     = int(cant or 0)
        nu_f       = float(nu or 0)
        tn_f       = float(tn or 0)

        # 4.1) Buscamos en orden_de_compra la fila cuyo “número de orden” = oc_int
        #      y cuyo art_corr = art_corr_i, para obtener su id real:
        oc_row = (
            supabase.table('orden_de_compra')
                    .select('id')
                    .eq('orden_compra', oc_int)
                    .eq('art_corr', str(art_corr_i))  # art_corr está guardado como varchar
                    .limit(1)
                    .execute()
                    .data or []
        )
        if not oc_row:
            # Si no existe coincidencia, simplemente saltamos esa línea
            continue

        oc_real_id = oc_row[0]['id']  # este es el valor que la FK espera

        # 4.2) Ahora obtenemos proyecto de esa misma OC (podría venir previo, pero así garantizamos)
        proj_rows = supabase.table('orden_de_compra') \
                            .select('proyecto') \
                            .eq('id', oc_real_id) \
                            .limit(1) \
                            .execute().data or []
        proyecto_val = proj_rows[0].get('proyecto') if proj_rows else None

        # 4.3) Material → id, tipo, item
        mat_rows = supabase.table('materiales') \
                          .select('id, tipo, item') \
                          .eq('material', desc) \
                          .limit(1) \
                          .execute().data or []
        mat = mat_rows[0] if mat_rows else {}
        mat_id   = mat.get('id')
        tipo_val = mat.get('tipo', '')
        item_val = mat.get('item', '')

        # 4.4) Mes de la factura (puedes omitirlo, o usarlo si tu modelo lo requiere)
        mes = int(fecha_factura.split('-')[1])

        # 4.5) Agregar al payload, usando oc_real_id como la clave foránea
        payload.append({
            'orden_numero':         numero,
            'proveedor':            proveedor_id,
            'proveedor_nombre':     nombre_proveedor,
            'autoriza':             autoriza_id,
            'autoriza_nombre':      f.get('autoriza_input', ''),
            'fecha':                hoy,
            'fecha_factura':        fecha_factura,
            'vencimiento':          fecha_vencimiento,
            'estado_pago':          estado_pago,
            'detalle_compra':       detalle_op,
            'factura':              "-".join(dict.fromkeys(guias)),
            'doc_recep':            "-".join(dict.fromkeys(guias)),
            # — Aquí va el ID real, no el número de OC:
            'orden_compra':         oc_real_id,
            'material':             mat_id,
            'material_nombre':      desc,
            'cantidad':             cant_i,
            'neto_unitario':        nu_f,
            'neto_total_recibido':  tn_f,
            'costo_final_con_iva':  nu_f * cant_i * 1.19,
            'forma_pago':           '0',
            'item':                 tipo_val,
            'tipo':                 item_val,
            'mes':                  mes,
            'art_corr':             art_corr_i,
            'n_ingreso':            n_ingreso_next,
            'proyecto':             proyecto_val
        })

        # Aumentamos el consecutivo de ingreso para la siguiente línea
        n_ingreso_next += 1

    # 5) Validar payload
    if not payload:
        flash("No se seleccionó ninguna línea.", "warning")
        return redirect(url_for('ordenes_pago.list_ordenes_pago', nombre_proveedor=nombre_proveedor))

    # 6) Insertar todas las líneas del payload
    supabase.table('orden_de_pago').insert(payload).execute()

    flash(f"Orden de pago #{numero} creada con {len(payload)} línea(s).", "success")
    return redirect(url_for('ordenes_pago.list_ordenes_pago', nombre_proveedor=nombre_proveedor))