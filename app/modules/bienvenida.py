from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user

bp_bienvenida = Blueprint('bienvenida', __name__)

@bp_bienvenida.route('/bienvenida')
@login_required
def bienvenida():
    supabase = current_app.config["SUPABASE"]
    # Total deuda: suma de costo_final_con_iva de orden_de_pago pendientes
    deuda_rows = supabase.table("orden_de_pago").select("costo_final_con_iva, fecha_pago").eq("estado_documento", "pendiente").execute().data or []
    total_deuda = sum(float(r.get("costo_final_con_iva") or 0) for r in deuda_rows if not r.get("fecha_pago"))

    # Órdenes pendientes: cantidad de orden_de_pago con estado_documento = pendiente
    ordenes_pendientes = len(deuda_rows)

    # Usuarios activos: usuarios con activo=True
    usuarios_rows = supabase.table("usuarios").select("id").eq("activo", True).execute().data or []
    usuarios_activos = len(usuarios_rows)

    # Proyectos en curso: proyectos con campo 'estado' = 'en_curso' o sin campo estado
    proyectos_rows = supabase.table("proyectos").select("id, estado").execute().data or []
    proyectos_en_curso = len([p for p in proyectos_rows if p.get("estado", "en_curso") == "en_curso"])

    return render_template(
        'bienvenida.html',
        total_deuda=total_deuda,
        ordenes_pendientes=ordenes_pendientes,
        usuarios_activos=usuarios_activos,
        proyectos_en_curso=proyectos_en_curso
    )
