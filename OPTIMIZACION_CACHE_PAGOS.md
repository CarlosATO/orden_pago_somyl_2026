# Optimización de Rendimiento - Módulo de Pagos

## Problema Original

El módulo de pagos tenía un problema de rendimiento crítico:
- **15 segundos** de tiempo de respuesta al filtrar por estado (Pendiente/Abono/Pagado)
- Causa: Cada request procesaba TODOS los registros (1219+ órdenes de pago) para calcular el estado

## Solución Implementada: Sistema de Caché

### 1. Arquitectura de Caché

```python
_pagos_cache = {
    "data": None,           # Lista completa de pagos procesados con estado
    "timestamp": 0,         # Momento de la última carga
    "ttl": 60              # Tiempo de vida: 60 segundos
}
```

### 2. Estrategia de Dos Caminos

#### Camino A: CON filtro de estado (usa caché)
1. Verificar si el caché es válido (< 60 segundos)
2. Si es válido: usar datos del caché (< 100ms)
3. Si expiró: llamar `obtener_todos_pagos_procesados()` (~2-3s una vez)
4. Guardar en caché con timestamp actual
5. Filtrar por estado deseado
6. Aplicar paginación manual (offset, limit)

#### Camino B: SIN filtro de estado (paginación normal)
1. Usar paginación nativa de Supabase
2. Obtener solo 50-100 registros
3. Procesar únicamente esos registros
4. Respuesta rápida (< 1s)

### 3. Funciones Clave

#### `obtener_todos_pagos_procesados(supabase, filtros_bd)`
- Obtiene TODOS los registros de orden_de_pago que cumplan filtros base
- Hace JOIN manual con fechas_de_pagos_op y abonos_op
- Calcula el estado para cada pago
- Retorna lista completa procesada

#### `calcular_estado_pago(fecha_pago, total_abonado, total_pago)`
- Lógica simplificada que coincide con sistema antiguo
- Si tiene fecha_pago → "pagado"
- Else si tiene abonos → "abono"
- Else → "pendiente"

#### `invalidar_cache_pagos()`
- Resetea el caché cuando se modifican datos
- Se llama en todos los endpoints POST/PUT/DELETE:
  - `update_fecha_pago()` - Al modificar fecha de pago
  - `create_abono()` - Al crear nuevo abono
  - `update_abono()` - Al editar abono
  - `delete_abono()` - Al eliminar abono

### 4. Mejoras de Rendimiento Esperadas

| Escenario | Antes | Después |
|-----------|-------|---------|
| Primera carga con filtro de estado | 15s | ~2-3s |
| Cargas subsecuentes (dentro de 60s) | 15s | < 100ms |
| Sin filtro de estado | 1s | 1s (sin cambio) |
| Después de modificar datos | 15s | ~2-3s (primera carga post-invalidación) |

### 5. Trade-offs

**Ventajas:**
- ✅ Respuesta instantánea dentro de ventana de 60s
- ✅ Reduce carga en base de datos
- ✅ No afecta queries sin filtro de estado
- ✅ Invalidación automática al modificar datos

**Desventajas:**
- ⚠️ Datos pueden estar hasta 60s desactualizados (entre modificaciones de usuarios diferentes)
- ⚠️ Consume memoria RAM (cache en servidor)
- ⚠️ Primera carga post-expiración aún toma 2-3s

### 6. Consideraciones Futuras

Si el rendimiento sigue siendo un problema, considerar:

1. **Redis Cache**: Mover caché a Redis para compartir entre instancias
2. **Materialized View**: Crear vista materializada en PostgreSQL con el estado pre-calculado
3. **Background Job**: Actualizar estados cada minuto con worker asíncrono
4. **WebSocket**: Notificar clientes cuando el caché se invalida

### 7. Monitoreo

Agregar logs para medir:
```python
logger.info(f"Cache hit! Procesado en {tiempo_procesamiento}ms")
logger.info(f"Cache miss. Recargando {total_registros} pagos...")
```

### 8. Testing

Probar:
- [ ] Filtrar por "Pendiente" (primera vez) → debe tomar ~2-3s
- [ ] Filtrar por "Pendiente" (segunda vez < 60s) → debe tomar < 100ms
- [ ] Modificar fecha de pago → verificar que invalide caché
- [ ] Filtrar por "Pendiente" después de modificación → debe recargar

## Código Modificado

- **Archivo**: `/nuevo_proyecto/backend/modules/pagos.py`
- **Líneas principales**:
  - 17-24: Definición de caché
  - 26-28: Función `invalidar_cache_pagos()`
  - 71-227: Función `obtener_todos_pagos_procesados()`
  - 230-320: Lógica de caché en `list_pagos()`
  - 800, 827, 947, 1107: Llamadas a `invalidar_cache_pagos()` en endpoints de modificación
