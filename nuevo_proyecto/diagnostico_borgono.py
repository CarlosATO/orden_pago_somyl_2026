"""
Script de diagnóstico para encontrar por qué BORGOÑO no cuadra
"""
import sys
sys.path.insert(0, 'backend')

from backend.app import create_app
from datetime import datetime

app = create_app()

with app.app_context():
    from flask import current_app
    supabase = current_app.config['SUPABASE']
    
    print('\n' + '=' * 80)
    print('DIAGNÓSTICO BORGOÑO - Simulando procesamiento del backend')
    print('=' * 80)
    
    proyecto_id = 30
    
    # 1. Obtener items
    res_items = supabase.table("item").select("id, tipo").order("tipo").execute()
    raw_items = res_items.data
    
    # Crear mapeos
    id_to_tipo = {}
    tipo_to_id = {}
    
    for it in raw_items:
        item_id = it.get('id')
        tipo_raw = it.get('tipo', '')
        
        # Normalizar tipo (eliminar plural)
        tipo = str(tipo_raw).upper().strip()
        if tipo.endswith('S') and len(tipo) > 3:
            tipo = tipo[:-1]
        
        id_to_tipo[item_id] = tipo
        tipo_to_id[tipo] = item_id
    
    print(f'\n✅ {len(raw_items)} items en la base de datos')
    
    # 2. Obtener órdenes de pago
    ordenes = supabase.table("orden_de_pago")\
        .select("proyecto, item, mes, costo_final_con_iva, fecha_factura")\
        .eq("proyecto", proyecto_id)\
        .not_.is_("fecha_factura", "null")\
        .execute()
    
    print(f'\n✅ {len(ordenes.data)} órdenes de pago obtenidas')
    
    # 3. Simular el procesamiento
    procesadas = 0
    saltadas = 0
    razones = {
        'item_no_normalizado': 0,
        'item_no_existe': 0,
        'sin_mes': 0,
        'mes_invalido': 0,
        'total': 0
    }
    
    total_procesado = 0
    total_saltado = 0
    
    print(f'\n📊 Procesando órdenes...\n')
    
    for op in ordenes.data:
        item_val = op.get('item')
        mes = op.get('mes')
        fecha_factura = op.get('fecha_factura')
        monto = float(op.get('costo_final_con_iva', 0) or 0)
        
        # Normalizar item
        item_id = None
        
        if isinstance(item_val, int):
            item_id = item_val if item_val in id_to_tipo else None
        else:
            tipo = str(item_val).upper().strip()
            if tipo:
                if tipo.endswith('S') and len(tipo) > 3:
                    tipo = tipo[:-1]
                item_id = tipo_to_id.get(tipo)
        
        if not item_id:
            saltadas += 1
            total_saltado += monto
            if isinstance(item_val, int):
                razones['item_no_existe'] += 1
                print(f'❌ SALTADA: Item ID {item_val} no existe en la BD - ${monto:,.0f}')
            else:
                razones['item_no_normalizado'] += 1
                print(f'❌ SALTADA: Item "{item_val}" no se pudo normalizar - ${monto:,.0f}')
            continue
        
        # Verificar mes
        if not mes:
            if fecha_factura:
                try:
                    if isinstance(fecha_factura, str):
                        fecha_obj = datetime.strptime(fecha_factura.split('T')[0], '%Y-%m-%d')
                        mes = fecha_obj.month
                    else:
                        mes = fecha_factura.month
                except:
                    saltadas += 1
                    total_saltado += monto
                    razones['mes_invalido'] += 1
                    print(f'❌ SALTADA: Fecha inválida {fecha_factura} - ${monto:,.0f}')
                    continue
            else:
                saltadas += 1
                total_saltado += monto
                razones['sin_mes'] += 1
                print(f'❌ SALTADA: Sin mes ni fecha - ${monto:,.0f}')
                continue
        
        # Si llegó aquí, se procesa
        procesadas += 1
        total_procesado += monto
    
    print(f'\n' + '=' * 80)
    print('RESULTADO')
    print('=' * 80)
    print(f'Órdenes procesadas: {procesadas}')
    print(f'Órdenes saltadas: {saltadas}')
    print(f'\n💰 Monto procesado: ${total_procesado:,.0f}')
    print(f'💰 Monto saltado: ${total_saltado:,.0f}')
    print(f'💰 TOTAL en BD: ${total_procesado + total_saltado:,.0f}')
    
    print(f'\n📋 Razones de salto:')
    for razon, cant in razones.items():
        if cant > 0:
            print(f'   {razon}: {cant}')
    
    print(f'\n🎯 Esperado en sistema antiguo: $22,300,736')
    print(f'🎯 Backend muestra: $20,732,528')
    print(f'🎯 Diferencia: ${22300736 - (total_procesado):,.0f}')
