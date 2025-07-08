-- 🚀 SCRIPT COMPLETO DE OPTIMIZACIÓN SUPABASE
-- Ejecutar en Supabase SQL Editor para máximo rendimiento
-- Versión: v2.0 - Optimización Integral

-- ========================================
-- 1. EXTENSIÓN REQUERIDA (EJECUTAR PRIMERO)
-- ========================================

-- Habilitar extensión pg_trgm para búsquedas similares
-- NOTA: Si ya está habilitada, esto no hará nada
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ========================================
-- 2. ÍNDICES PRINCIPALES PARA MATERIALES 
-- ========================================

-- Índices B-tree estándar para búsquedas exactas y ordenamiento
CREATE INDEX IF NOT EXISTS idx_materiales_cod_btree ON materiales USING btree (cod);
CREATE INDEX IF NOT EXISTS idx_materiales_material_btree ON materiales USING btree (material);

-- Índices GIN para búsquedas ILIKE súper-rápidas
CREATE INDEX IF NOT EXISTS idx_materiales_cod_ilike ON materiales USING gin (cod gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_materiales_material_ilike ON materiales USING gin (material gin_trgm_ops);

-- Índice compuesto para búsquedas múltiples (material + código)
CREATE INDEX IF NOT EXISTS idx_materiales_search ON materiales USING btree (material, cod);

-- Índice para campos tipo e item (consultas frecuentes)
CREATE INDEX IF NOT EXISTS idx_materiales_tipo_item ON materiales USING btree (tipo, item);

-- ========================================
-- 3. ÍNDICES PARA ORDEN_DE_COMPRA (CRÍTICOS)
-- ========================================

-- Índice único para art_corr (clave primaria alternativa)
CREATE UNIQUE INDEX IF NOT EXISTS idx_oc_artcorr ON orden_de_compra USING btree (art_corr);

-- Índice optimizado para consultas de precios históricos
CREATE INDEX IF NOT EXISTS idx_orden_compra_precio_lookup 
ON orden_de_compra USING btree (descripcion, fecha DESC, precio_unitario) 
WHERE precio_unitario IS NOT NULL AND precio_unitario > 0;

-- Índice para búsquedas por número de OC (ingresos)
CREATE INDEX IF NOT EXISTS idx_orden_compra_numero ON orden_de_compra USING btree (orden_compra);
CREATE INDEX IF NOT EXISTS idx_orden_compra_numero_ilike ON orden_de_compra USING gin ((orden_compra::text) gin_trgm_ops);

-- Índice por fecha para reportes y consultas temporales
CREATE INDEX IF NOT EXISTS idx_orden_compra_fecha ON orden_de_compra USING btree (fecha DESC);

-- Índice compuesto para consultas por proveedor y proyecto
CREATE INDEX IF NOT EXISTS idx_orden_compra_proveedor_proyecto ON orden_de_compra USING btree (proveedor, proyecto);

-- ========================================
-- 4. ÍNDICES PARA PROVEEDORES
-- ========================================

-- Índice GIN para búsquedas ILIKE en nombre (APIs Select2)
CREATE INDEX IF NOT EXISTS idx_proveedores_nombre_ilike ON proveedores USING gin (nombre gin_trgm_ops);

-- Índice B-tree para búsquedas exactas y ordenamiento
CREATE INDEX IF NOT EXISTS idx_proveedores_nombre_btree ON proveedores USING btree (nombre);

-- Índice para RUT (búsquedas exactas)
CREATE INDEX IF NOT EXISTS idx_proveedores_rut ON proveedores USING btree (rut);

-- ========================================
-- 5. ÍNDICES PARA PROYECTOS
-- ========================================

-- Índice GIN para búsquedas ILIKE en proyecto
CREATE INDEX IF NOT EXISTS idx_proyectos_proyecto_ilike ON proyectos USING gin (proyecto gin_trgm_ops);

-- Índice B-tree para búsquedas exactas
CREATE INDEX IF NOT EXISTS idx_proyectos_proyecto_btree ON proyectos USING btree (proyecto);

-- ========================================
-- 6. ÍNDICES PARA TRABAJADORES
-- ========================================

-- Índice GIN para búsquedas ILIKE en nombre
CREATE INDEX IF NOT EXISTS idx_trabajadores_nombre_ilike ON trabajadores USING gin (nombre gin_trgm_ops);

-- Índice B-tree para búsquedas exactas
CREATE INDEX IF NOT EXISTS idx_trabajadores_nombre_btree ON trabajadores USING btree (nombre);

-- Índice para email (si existe)
CREATE INDEX IF NOT EXISTS idx_trabajadores_correo ON trabajadores USING btree (correo);

-- ========================================
-- 7. ÍNDICES PARA PLAZOS_PAGO Y TIPOS_ENTREGA
-- ========================================

-- Plazos de pago
CREATE INDEX IF NOT EXISTS idx_plazos_pago_plazo_ilike ON plazos_pago USING gin (plazo gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_plazos_pago_plazo_btree ON plazos_pago USING btree (plazo);

-- Tipos de entrega
CREATE INDEX IF NOT EXISTS idx_tipos_entrega_tipo_ilike ON tipos_entrega USING gin (tipo gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_tipos_entrega_tipo_btree ON tipos_entrega USING btree (tipo);

-- ========================================
-- 8. ÍNDICES PARA ITEMS (TIPOS)
-- ========================================

-- Índice GIN para búsquedas ILIKE en tipo
CREATE INDEX IF NOT EXISTS idx_items_tipo_ilike ON item USING gin (tipo gin_trgm_ops);

-- Índice B-tree para búsquedas exactas
CREATE INDEX IF NOT EXISTS idx_items_tipo_btree ON item USING btree (tipo);

-- ========================================
-- 9. ÍNDICES PARA USUARIOS
-- ========================================

-- Índice GIN para búsquedas ILIKE en nombre
CREATE INDEX IF NOT EXISTS idx_usuarios_nombre_ilike ON usuarios USING gin (nombre gin_trgm_ops);

-- Índice único para email (login)
CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios USING btree (email);

-- Índice para búsquedas por nombre
CREATE INDEX IF NOT EXISTS idx_usuarios_nombre_btree ON usuarios USING btree (nombre);

-- ========================================
-- 10. ÍNDICES PARA ORDENES_PAGO
-- ========================================

-- Índice por fecha para reportes
CREATE INDEX IF NOT EXISTS idx_ordenes_pago_fecha ON ordenes_pago USING btree (fecha DESC);

-- Índice por estado para consultas de pendientes
CREATE INDEX IF NOT EXISTS idx_ordenes_pago_estado ON ordenes_pago USING btree (estado);

-- Índice por proveedor
CREATE INDEX IF NOT EXISTS idx_ordenes_pago_proveedor ON ordenes_pago USING btree (proveedor_id);

-- Índice compuesto para consultas complejas
CREATE INDEX IF NOT EXISTS idx_ordenes_pago_lookup ON ordenes_pago USING btree (estado, fecha DESC, proveedor_id);

-- ========================================
-- 11. ÍNDICES PARA INGRESOS
-- ========================================

-- Índice por fecha para reportes
CREATE INDEX IF NOT EXISTS idx_ingresos_fecha ON ingresos USING btree (fecha DESC);

-- Índice por orden de compra (relación con OC)
CREATE INDEX IF NOT EXISTS idx_ingresos_oc ON ingresos USING btree (orden_compra);

-- Índice compuesto para consultas por OC y fecha
CREATE INDEX IF NOT EXISTS idx_ingresos_oc_fecha ON ingresos USING btree (orden_compra, fecha DESC);

-- ========================================
-- 12. ÍNDICES PARA PRESUPUESTOS
-- ========================================

-- Índice por proyecto
CREATE INDEX IF NOT EXISTS idx_presupuesto_proyecto ON presupuesto USING btree (proyecto);

-- Índice por item
CREATE INDEX IF NOT EXISTS idx_presupuesto_item ON presupuesto USING btree (item);

-- Índice compuesto proyecto-item
CREATE INDEX IF NOT EXISTS idx_presupuesto_proyecto_item ON presupuesto USING btree (proyecto, item);

-- ========================================
-- 13. ÍNDICES PARA GASTOS_DIRECTOS
-- ========================================

-- Índice por proyecto
CREATE INDEX IF NOT EXISTS idx_gastos_directos_proyecto ON gastos_directos USING btree (proyecto_id);

-- Índice por fecha y mes
CREATE INDEX IF NOT EXISTS idx_gastos_directos_fecha ON gastos_directos USING btree (fecha DESC);
CREATE INDEX IF NOT EXISTS idx_gastos_directos_mes ON gastos_directos USING btree (mes);

-- Índice compuesto para reportes
CREATE INDEX IF NOT EXISTS idx_gastos_directos_lookup ON gastos_directos USING btree (proyecto_id, mes, fecha DESC);

-- ========================================
-- 14. VERIFICACIÓN Y ESTADÍSTICAS
-- ========================================

-- Ejecutar DESPUÉS de crear todos los índices para verificar:

-- 1. Ver todos los índices creados
/*
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
*/

-- 2. Ver estadísticas de uso de índices (ejecutar después de usar la app)
/*
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as "Veces_usado",
    idx_tup_read as "Tuplas_leídas",
    idx_tup_fetch as "Tuplas_obtenidas"
FROM pg_stat_user_indexes 
WHERE tablename IN ('materiales', 'orden_de_compra', 'proveedores', 'proyectos', 'trabajadores', 'ordenes_pago', 'ingresos')
  AND indexname LIKE 'idx_%'
ORDER BY idx_scan DESC;
*/

-- 3. Ver tamaño de índices
/*
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as "Tamaño"
FROM pg_indexes 
WHERE schemaname = 'public' 
  AND indexname LIKE 'idx_%'
ORDER BY pg_relation_size(indexname::regclass) DESC;
*/

-- ========================================
-- INSTRUCCIONES DE USO
-- ========================================

/*
1. EJECUTAR TODO EL SCRIPT EN SUPABASE SQL EDITOR
2. Los índices se crearán automáticamente (IF NOT EXISTS previene errores)
3. La extensión pg_trgm debe estar habilitada (línea 8)
4. Después de usar la app, ejecutar las consultas de verificación
5. Los índices mejorarán automáticamente el rendimiento

IMPACTO ESPERADO:
- Búsquedas de materiales: <100ms (antes: 2-3 segundos)
- APIs Select2: instantáneas (<50ms)
- Carga de formularios: 80%+ más rápida
- Navegación entre módulos: fluida

MANTENIMIENTO:
- Los índices se mantienen automáticamente
- PostgreSQL los usará automáticamente en consultas apropiadas
- Monitorear el uso con las consultas de estadísticas
*/
