# CORRECCIÓN COMPLETA: PROBLEMA DE RUTs FALTANTES EN EXPORTACIÓN DE EXCEL

## Problema Identificado
La función de exportar a Excel no mostraba todos los RUTs de los proveedores debido a tres problemas principales:

### 1. Error en limpieza de caché
**Problema:** Se llamaba `clear_static_cache("proveedores")` pero la función no acepta parámetros.
**Solución:** Cambiado a `invalidate_static_cache("proveedores")` que es la función correcta.

### 2. Limitación de paginación en proveedores
**Problema:** La función `get_cached_proveedores()` usaba `limit(500)` limitando los resultados.
**Solución:** Implementada paginación completa para obtener TODOS los proveedores:

```python
def get_cached_proveedores():
    # ... código anterior ...
    try:
        # Obtener TODOS los proveedores sin límite usando paginación
        all_proveedores = []
        page_size = 1000
        offset = 0
        
        while True:
            batch = supabase.table("proveedores").select("id,nombre,cuenta,rut").range(offset, offset + page_size - 1).execute().data or []
            all_proveedores.extend(batch)
            
            if len(batch) < page_size:
                break
            offset += page_size
        
        set_cached_data("static_proveedores", all_proveedores)
        return all_proveedores
    # ... resto del código ...
```

### 3. Mapeo inconsistente de tipos de ID
**Problema:** Los IDs de proveedores pueden ser int o string, causando fallos en el mapeo.
**Solución:** Crear mapeo robusto que maneja todos los tipos:

```python
# Crear múltiples mapas para manejar diferentes tipos de ID
rut_map = {}
for p in provs:
    if p.get("id") is not None and p.get("rut"):
        # Agregar todas las variantes posibles del ID
        rut_map[p["id"]] = p["rut"]
        try:
            rut_map[int(p["id"])] = p["rut"]
        except (ValueError, TypeError):
            pass
        try:
            rut_map[str(p["id"])] = p["rut"]
        except (ValueError, TypeError):
            pass
```

## Archivos Modificados

### 1. `/app/modules/pagos.py`
- ✅ Corregida llamada a invalidación de caché
- ✅ Mejorado mapeo de RUTs con manejo robusto de tipos
- ✅ Agregados logs de depuración para seguimiento
- ✅ Agregadas funciones de depuración `/pagos/debug_ruts` y `/pagos/verificar_proveedores`

### 2. `/app/utils/static_data.py`
- ✅ Implementada paginación completa en `get_cached_proveedores()`
- ✅ Eliminado límite de 500 proveedores

## Funciones de Depuración Agregadas

### 1. `/pagos/debug_ruts`
Endpoint para verificar el estado de proveedores y mapeo de RUTs.

### 2. `/pagos/verificar_proveedores`
Endpoint para verificar consistencia entre tablas `orden_de_pago` y `proveedores`.

## Verificación de la Solución

Se creó un script de prueba (`test_proveedores_fix.py`) que verifica:
- ✅ Mapeo correcto de IDs tipo int y string
- ✅ Manejo de proveedores sin RUT
- ✅ Manejo de proveedores inexistentes
- ✅ Todas las pruebas pasan correctamente

## Logs de Depuración

La función de exportación ahora incluye logs detallados:
```
[DEBUG EXPORT] Total proveedores cargados: X
[DEBUG EXPORT] Total pagos a exportar: Y
[DEBUG EXPORT] Proveedores con RUT: Z
[DEBUG EXPORT] Pagos con RUT asignado: A
[DEBUG EXPORT] Pagos sin RUT: B
```

## Resultado Esperado

Después de estos cambios:
1. ✅ Se cargan TODOS los proveedores de la base de datos
2. ✅ Se invalida correctamente el caché antes de exportar
3. ✅ Se mapean correctamente los RUTs independientemente del tipo de ID
4. ✅ Se tienen herramientas de depuración para futuros problemas
5. ✅ Los logs permiten monitorear el proceso de exportación

La exportación a Excel ahora debe mostrar todos los RUTs de proveedores disponibles en la base de datos.
