"""
Script COMPLETO para diagnosticar ENTEL ARCOS LONGAVÍ - Proyecto 55
Investiga:
1. Órdenes de pago con fecha_factura
2. Órdenes de pago SIN fecha_factura
3. Gastos directos
4. Búsqueda por nombre de proyecto en lugar de ID
"""
import sys
import os
from pathlib import Path

# Configurar path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir / 'nuevo_proyecto' / 'backend'))

# Usar el contexto de Flask
from app import create_app

app = create_app()

with app.app_context():
    from flask import current_app
    supabase = current_app.config['SUPABASE']
    
    print("\n" + "=" * 80)
    print("DIAGNÓSTICO COMPLETO - ENTEL ARCOS LONGAVÍ")
    print("=" * 80)
    
    # 1. Verificar proyecto
    proy = supabase.table('proyectos').select('*').eq('id', 55).execute()
    if proy.data:
        print(f"\n📋 Proyecto encontrado:")
        print(f"   ID: {proy.data[0]['id']}")
        print(f"   Nombre: {proy.data[0]['proyecto']}")
        print(f"   Activo: {proy.data[0].get('activo')}")
        print(f"   Observación: {proy.data[0].get('observacion')}")
    
    # 2. Órdenes de pago CON fecha_factura (las que usa el backend)
    print("\n" + "=" * 80)
    print("ÓRDENES DE PAGO CON FECHA_FACTURA")
    print("=" * 80)
    
    ops_con_fecha = supabase.table('orden_de_pago')\
        .select('*')\
        .eq('proyecto', 55)\
        .not_.is_('fecha_factura', 'null')\
        .execute()
    
    print(f"\n📊 Total: {len(ops_con_fecha.data)} órdenes")
    total_con_fecha = 0
    
    for op in ops_con_fecha.data:
        monto = op.get('costo_final_con_iva', 0) or 0
        total_con_fecha += monto
        print(f"  - ID {op['id']}: {op.get('item')} / Mes {op.get('mes')} = ${monto:,.0f}")
    
    print(f"\n💰 TOTAL CON FECHA: ${total_con_fecha:,.0f}")
    
    # 3. Órdenes de pago SIN fecha_factura (las que el backend IGNORA)
    print("\n" + "=" * 80)
    print("ÓRDENES DE PAGO SIN FECHA_FACTURA (IGNORADAS POR EL BACKEND)")
    print("=" * 80)
    
    ops_sin_fecha = supabase.table('orden_de_pago')\
        .select('*')\
        .eq('proyecto', 55)\
        .is_('fecha_factura', 'null')\
        .execute()
    
    print(f"\n📊 Total: {len(ops_sin_fecha.data)} órdenes")
    total_sin_fecha = 0
    
    for op in ops_sin_fecha.data:
        monto = op.get('costo_final_con_iva', 0) or 0
        total_sin_fecha += monto
        print(f"  - ID {op['id']}: {op.get('item')} / Mes {op.get('mes')} = ${monto:,.0f}")
    
    print(f"\n💰 TOTAL SIN FECHA: ${total_sin_fecha:,.0f}")
    
    # 4. TODAS las órdenes de pago
    print("\n" + "=" * 80)
    print("TODAS LAS ÓRDENES DE PAGO")
    print("=" * 80)
    
    ops_todas = supabase.table('orden_de_pago')\
        .select('*')\
        .eq('proyecto', 55)\
        .execute()
    
    total_todas = sum(op.get('costo_final_con_iva', 0) or 0 for op in ops_todas.data)
    print(f"\n📊 Total: {len(ops_todas.data)} órdenes")
    print(f"💰 TOTAL TODAS: ${total_todas:,.0f}")
    
    # 5. Gastos directos
    print("\n" + "=" * 80)
    print("GASTOS DIRECTOS")
    print("=" * 80)
    
    gastos = supabase.table('gastos_directos')\
        .select('*')\
        .eq('proyecto_id', 55)\
        .execute()
    
    print(f"\n📊 Total: {len(gastos.data)} gastos directos")
    total_gastos = 0
    
    gastos_por_mes = {}
    for gasto in gastos.data:
        monto = gasto.get('monto', 0) or 0
        mes = gasto.get('mes', 'Sin mes')
        total_gastos += monto
        
        if mes not in gastos_por_mes:
            gastos_por_mes[mes] = 0
        gastos_por_mes[mes] += monto
    
    if gastos.data:
        print("\n  Por mes:")
        for mes in sorted(gastos_por_mes.keys()):
            print(f"    {mes}: ${gastos_por_mes[mes]:,.0f}")
    
    print(f"\n💰 TOTAL GASTOS DIRECTOS: ${total_gastos:,.0f}")
    
    # 6. RESUMEN FINAL
    print("\n" + "=" * 80)
    print("RESUMEN TOTAL")
    print("=" * 80)
    print(f"\nÓrdenes con fecha_factura:    ${total_con_fecha:,.0f}  ← LO QUE USA EL BACKEND")
    print(f"Órdenes sin fecha_factura:    ${total_sin_fecha:,.0f}  ← IGNORADAS")
    print(f"Todas las órdenes:            ${total_todas:,.0f}")
    print(f"Gastos directos:              ${total_gastos:,.0f}")
    print(f"=" * 80)
    print(f"GRAN TOTAL:                   ${total_con_fecha + total_gastos:,.0f}")
    print(f"TOTAL SI INCLUYERA TODO:      ${total_todas + total_gastos:,.0f}")
    print(f"=" * 80)
    print(f"\n❓ El usuario esperaba: $724,000")
    print(f"❓ El backend muestra:  ${total_con_fecha + total_gastos:,.0f}")
    print(f"❓ Diferencia:          ${724000 - (total_con_fecha + total_gastos):,.0f}")
