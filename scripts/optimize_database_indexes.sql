-- Script de optimización de índices para mejorar rendimiento de consultas
-- Ejecutar en Supabase SQL Editor

-- 1. Índice compuesto para búsqueda de materiales por nombre y código
-- Esto optimizará significativamente las consultas de api_materiales
CREATE INDEX IF NOT EXISTS idx_materiales_search 
ON materiales (material, cod);

-- 2. Índice específico para búsqueda ILIKE en material
CREATE INDEX IF NOT EXISTS idx_materiales_material_ilike 
ON materiales USING gin (material gin_trgm_ops);

-- 3. Índice específico para búsqueda ILIKE en código
CREATE INDEX IF NOT EXISTS idx_materiales_cod_ilike 
ON materiales USING gin (cod gin_trgm_ops);

-- 4. Índice optimizado para orden_de_compra para búsqueda de últimos precios
-- Esto mejorará mucho la consulta de histórico de precios
CREATE INDEX IF NOT EXISTS idx_orden_compra_precio_lookup 
ON orden_de_compra (descripcion, orden_compra DESC, fecha DESC) 
WHERE precio_unitario IS NOT NULL AND precio_unitario > 0;

-- 5. Índice adicional para orden_de_compra por fecha descendente
CREATE INDEX IF NOT EXISTS idx_orden_compra_fecha_desc 
ON orden_de_compra (fecha DESC, descripcion);

-- 6. Índice para proveedores por nombre (para api_proveedores)
CREATE INDEX IF NOT EXISTS idx_proveedores_nombre_ilike 
ON proveedores USING gin (nombre gin_trgm_ops);

-- 7. Índice para proyectos por nombre
CREATE INDEX IF NOT EXISTS idx_proyectos_proyecto_ilike 
ON proyectos USING gin (proyecto gin_trgm_ops);

-- 8. Índice para trabajadores por nombre
CREATE INDEX IF NOT EXISTS idx_trabajadores_nombre_ilike 
ON trabajadores USING gin (nombre gin_trgm_ops);

-- 9. Activar extensión pg_trgm si no está activada (necesaria para los índices GIN)
-- NOTA: Esto debe ejecutarse como superusuario en Supabase
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 10. Estadísticas para verificar uso de índices
-- Ejecutar después de crear los índices para ver su efectividad:
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

-- INSTRUCCIONES DE USO:
-- 1. Copiar y pegar este script en el SQL Editor de Supabase
-- 2. Ejecutar línea por línea o todo el script
-- 3. Los índices mejorarán automáticamente el rendimiento
-- 4. Monitorear el rendimiento antes y después de crear los índices

-- NOTA IMPORTANTE:
-- La extensión pg_trgm debe estar habilitada para los índices GIN
-- Si tienes permisos de superusuario, descomenta la línea CREATE EXTENSION
-- Si no, contacta al administrador de la base de datos
