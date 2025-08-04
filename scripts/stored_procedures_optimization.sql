-- 🚀 STORED PROCEDURE PARA OPTIMIZAR CÁLCULO DE PENDIENTES
-- Ejecutar en Supabase SQL Editor después de los índices principales

-- ========================================
-- FUNCIÓN OPTIMIZADA PARA TOTAL PENDIENTE
-- ========================================

CREATE OR REPLACE FUNCTION get_total_pendiente_optimized()
RETURNS TABLE(total_pendiente NUMERIC) AS $$
BEGIN
    RETURN QUERY
    WITH pagos_agrupados AS (
        -- Agregar órdenes de pago por número
        SELECT 
            op.orden_numero,
            SUM(COALESCE(op.costo_final_con_iva, 0)) as total_orden
        FROM orden_de_pago op
        GROUP BY op.orden_numero
    ),
    pagos_realizados AS (
        -- Obtener órdenes que ya tienen fecha de pago
        SELECT DISTINCT fp.orden_numero
        FROM fechas_de_pagos_op fp
        WHERE fp.fecha_pago IS NOT NULL
    )
    -- Sumar solo las órdenes que NO están en pagos_realizados
    SELECT 
        COALESCE(SUM(pa.total_orden), 0) as total_pendiente
    FROM pagos_agrupados pa
    LEFT JOIN pagos_realizados pr ON pa.orden_numero = pr.orden_numero
    WHERE pr.orden_numero IS NULL;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- FUNCIÓN PARA CONTAR PENDIENTES SIN FACTURA
-- ========================================

CREATE OR REPLACE FUNCTION get_pendientes_sin_factura_count()
RETURNS TABLE(total_count BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT COUNT(*) as total_count
    FROM orden_de_pago
    WHERE estado_documento = 'pendiente';
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- FUNCIÓN OPTIMIZADA PARA BÚSQUEDA DE MATERIALES
-- ========================================

CREATE OR REPLACE FUNCTION search_materiales_optimized(search_term TEXT)
RETURNS TABLE(
    cod TEXT,
    material TEXT,
    tipo TEXT,
    item TEXT,
    precio_sugerido NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH materiales_encontrados AS (
        SELECT 
            m.cod,
            m.material,
            m.tipo,
            m.item
        FROM materiales m
        WHERE 
            m.material ILIKE '%' || search_term || '%' 
            OR m.cod ILIKE '%' || search_term || '%'
        ORDER BY 
            CASE 
                WHEN m.material ILIKE search_term || '%' THEN 1
                WHEN m.cod ILIKE search_term || '%' THEN 2
                ELSE 3
            END,
            m.material
        LIMIT 15
    ),
    precios_sugeridos AS (
        SELECT DISTINCT ON (oc.descripcion)
            oc.descripcion,
            oc.precio_unitario
        FROM orden_de_compra oc
        INNER JOIN materiales_encontrados me ON oc.descripcion = me.material
        WHERE oc.precio_unitario IS NOT NULL AND oc.precio_unitario > 0
        ORDER BY oc.descripcion, oc.fecha DESC
    )
    SELECT 
        me.cod,
        me.material,
        me.tipo,
        me.item,
        COALESCE(ps.precio_unitario, 0) as precio_sugerido
    FROM materiales_encontrados me
    LEFT JOIN precios_sugeridos ps ON me.material = ps.descripcion;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- ÍNDICES ADICIONALES PARA STORED PROCEDURES
-- ========================================

-- Índice para optimizar la función de pendientes
CREATE INDEX IF NOT EXISTS idx_orden_pago_numero_costo 
ON orden_de_pago USING btree (orden_numero, costo_final_con_iva);

-- Índice para fechas de pago no nulas
CREATE INDEX IF NOT EXISTS idx_fechas_pago_not_null 
ON fechas_de_pagos_op USING btree (orden_numero) 
WHERE fecha_pago IS NOT NULL;

-- Índice para estado pendiente en orden_de_pago
CREATE INDEX IF NOT EXISTS idx_orden_pago_estado_pendiente 
ON orden_de_pago USING btree (estado_documento) 
WHERE estado_documento = 'pendiente';

-- ========================================
-- VERIFICACIÓN DE FUNCIONES CREADAS
-- ========================================

-- Verificar que las funciones se crearon correctamente
DO $$
BEGIN
    -- Verificar función de pendientes
    IF EXISTS (
        SELECT 1 FROM pg_proc 
        WHERE proname = 'get_total_pendiente_optimized'
    ) THEN
        RAISE NOTICE '✅ Función get_total_pendiente_optimized creada correctamente';
    ELSE
        RAISE WARNING '❌ Error creando función get_total_pendiente_optimized';
    END IF;
    
    -- Verificar función de conteo
    IF EXISTS (
        SELECT 1 FROM pg_proc 
        WHERE proname = 'get_pendientes_sin_factura_count'
    ) THEN
        RAISE NOTICE '✅ Función get_pendientes_sin_factura_count creada correctamente';
    ELSE
        RAISE WARNING '❌ Error creando función get_pendientes_sin_factura_count';
    END IF;
    
    -- Verificar función de búsqueda
    IF EXISTS (
        SELECT 1 FROM pg_proc 
        WHERE proname = 'search_materiales_optimized'
    ) THEN
        RAISE NOTICE '✅ Función search_materiales_optimized creada correctamente';
    ELSE
        RAISE WARNING '❌ Error creando función search_materiales_optimized';
    END IF;
END $$;

-- ========================================
-- COMENTARIOS PARA DOCUMENTACIÓN
-- ========================================

COMMENT ON FUNCTION get_total_pendiente_optimized() IS 'Calcula el total pendiente de pago usando agregación SQL optimizada';
COMMENT ON FUNCTION get_pendientes_sin_factura_count() IS 'Cuenta órdenes de pago pendientes sin factura';
COMMENT ON FUNCTION search_materiales_optimized(TEXT) IS 'Búsqueda optimizada de materiales con precios sugeridos';
