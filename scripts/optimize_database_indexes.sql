-- Script de optimización de índices para mejorar rendimiento de consultas
-- Ejecutar en Supabase SQL Editor

-- ========================================
-- ÍNDICES PRINCIPALES PARA MATERIALES
-- ========================================

-- 1. Índice compuesto para búsqueda de materiales por nombre y código
CREATE INDEX IF NOT EXISTS idx_materiales_search 
ON materiales (material, cod);

-- 2. Índice específico para búsqueda ILIKE en material
CREATE INDEX IF NOT EXISTS idx_materiales_material_ilike 
ON materiales USING gin (material gin_trgm_ops);

-- 3. Índice específico para búsqueda ILIKE en código
CREATE INDEX IF NOT EXISTS idx_materiales_cod_ilike 
ON materiales USING gin (cod gin_trgm_ops);

-- ========================================
-- ÍNDICES PARA ORDEN_DE_COMPRA
-- ========================================

-- 4. Índice optimizado para búsqueda de últimos precios
CREATE INDEX IF NOT EXISTS idx_orden_compra_precio_lookup 
ON orden_de_compra (descripcion, orden_compra DESC, fecha DESC) 
WHERE precio_unitario IS NOT NULL AND precio_unitario > 0;

-- 5. Índice para búsquedas por número de OC
CREATE INDEX IF NOT EXISTS idx_orden_compra_numero_ilike 
ON orden_de_compra USING gin (orden_compra::text gin_trgm_ops);

-- ========================================
-- ÍNDICES PARA APIS DE SELECT2
-- ========================================

-- 6. Índice para proveedores por nombre
CREATE INDEX IF NOT EXISTS idx_proveedores_nombre_ilike 
ON proveedores USING gin (nombre gin_trgm_ops);

-- 7. Índice para proyectos por nombre
CREATE INDEX IF NOT EXISTS idx_proyectos_proyecto_ilike 
ON proyectos USING gin (proyecto gin_trgm_ops);

-- 8. Índice para trabajadores por nombre
CREATE INDEX IF NOT EXISTS idx_trabajadores_nombre_ilike 
ON trabajadores USING gin (nombre gin_trgm_ops);

-- ========================================
-- ÍNDICES ADICIONALES PARA OTRAS TABLAS
-- ========================================

-- 9. Índices para plazos_pago
CREATE INDEX IF NOT EXISTS idx_plazos_pago_plazo_ilike 
ON plazos_pago USING gin (plazo gin_trgm_ops);

-- 10. Índices para tipos_entrega
CREATE INDEX IF NOT EXISTS idx_tipos_entrega_tipo_ilike 
ON tipos_entrega USING gin (tipo gin_trgm_ops);

-- 11. Índices para usuarios (si necesitan búsqueda)
CREATE INDEX IF NOT EXISTS idx_usuarios_nombre_ilike 
ON usuarios USING gin (nombre gin_trgm_ops);

-- ========================================
-- EXTENSIÓN REQUERIDA
-- ========================================

-- 12. Activar extensión pg_trgm (necesaria para índices GIN)
-- NOTA: Debe ejecutarse como superusuario en Supabase
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ========================================
-- VERIFICACIÓN DE ÍNDICES
-- ========================================

-- Consulta para verificar índices creados:
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

-- Consulta para verificar uso de índices:
/*
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as "Veces usado",
    idx_tup_read as "Tuplas leídas",
    idx_tup_fetch as "Tuplas obtenidas"
FROM pg_stat_user_indexes 
WHERE tablename IN ('materiales', 'orden_de_compra', 'proveedores', 'proyectos', 'trabajadores')
ORDER BY idx_scan DESC;
*/

-- "Desarrollado por Carlos Alegría | SOMYL 2025"
