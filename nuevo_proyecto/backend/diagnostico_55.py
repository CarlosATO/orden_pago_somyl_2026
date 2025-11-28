"""
Script para diagnosticar ENTEL ARCOS LONGAVÍ - Proyecto 55
Se ejecuta desde el directorio backend
"""
from app import create_app

app = create_app()

with app.app_context():
    from flask import current_app
    supabase = current_app.config['SUPABASE']
    
    print("\n" + "=" * 80)
    print("DIAGNÓSTICO COMPLETO - ENTEL ARCOS LONGAVÍ (ID 55)")
    print("=" * 80)
    
    # 1. Verificar proyecto
    proy = supabase.table('proyectos').select('*').eq('id', 55).execute()
    if proy.data:
        print(f"\n📋 Proyecto:")
        print(f"   ID: {proy.data[0]['id']}")
        print(f"   Nombre: {proy.data[0]['proyecto']}")
        print(f"   Activo: {proy.data[0].get('activo')}")
    
    # 2. Órdenes CON fecha_factura (las que cuenta el backend)
    print("\n" + "=" * 80)
    print("ÓRDENES DE PAGO CON FECHA_FACTURA (usadas por backend)")
    print("=" * 80)
    
    ops_con = supabase.table('orden_de_pago')\
        .select('*')\
        .eq('proyecto', 55)\
        .not_.is_('fecha_factura', 'null')\
        .execute()
    
    total_con = sum(op.get('costo_final_con_iva', 0) or 0 for op in ops_con.data)
    print(f"📊 Total: {len(ops_con.data)} órdenes")
    print(f"💰 Monto: ${total_con:,.0f}")
    for op in ops_con.data:
        m = op.get('costo_final_con_iva', 0) or 0
        print(f"   ID {op['id']}: {op.get('item')} / Mes {op.get('mes')} = ${m:,.0f}")
    
    # 3. Órdenes SIN fecha_factura (ignoradas)
    print("\n" + "=" * 80)
    print("ÓRDENES SIN FECHA_FACTURA (ignoradas por backend)")
    print("=" * 80)
    
    ops_sin = supabase.table('orden_de_pago')\
        .select('*')\
        .eq('proyecto', 55)\
        .is_('fecha_factura', 'null')\
        .execute()
    
    total_sin = sum(op.get('costo_final_con_iva', 0) or 0 for op in ops_sin.data)
    print(f"📊 Total: {len(ops_sin.data)} órdenes")
    print(f"💰 Monto: ${total_sin:,.0f}")
    for op in ops_sin.data:
        m = op.get('costo_final_con_iva', 0) or 0
        print(f"   ID {op['id']}: {op.get('item')} / Mes {op.get('mes')} = ${m:,.0f}")
    
    # 4. Gastos directos
    print("\n" + "=" * 80)
    print("GASTOS DIRECTOS")
    print("=" * 80)
    
    gastos = supabase.table('gastos_directos')\
        .select('*')\
        .eq('proyecto_id', 55)\
        .execute()
    
    total_gastos = sum(g.get('monto', 0) or 0 for g in gastos.data)
    print(f"📊 Total: {len(gastos.data)} gastos")
    print(f"💰 Monto: ${total_gastos:,.0f}")
    
    # 5. RESUMEN
    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Órdenes CON fecha:    ${total_con:,.0f}  ← BACKEND USA ESTO")
    print(f"Órdenes SIN fecha:    ${total_sin:,.0f}  ← IGNORADAS")
    print(f"Gastos directos:      ${total_gastos:,.0f}")
    print("=" * 80)
    print(f"BACKEND CALCULA:      ${total_con + total_gastos:,.0f}")
    print(f"SI USARA TODO:        ${total_con + total_sin + total_gastos:,.0f}")
    print("=" * 80)
    print(f"\nUsuario esperaba: $724,000")
    print(f"Backend muestra:  ${total_con + total_gastos:,.0f}")
    print(f"Diferencia:       ${724000 - (total_con + total_gastos):,.0f}")
