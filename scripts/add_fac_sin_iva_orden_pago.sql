-- Script para agregar la columna fac_sin_iva a la tabla orden_de_pago
-- Esta columna almacena si la orden de pago es sin IVA (0 = con IVA, 1 = sin IVA)

-- Agregar la columna fac_sin_iva
ALTER TABLE orden_de_pago 
ADD COLUMN IF NOT EXISTS fac_sin_iva INTEGER DEFAULT 0;

-- Actualizar registros existentes basado en la orden de compra original
UPDATE orden_de_pago 
SET fac_sin_iva = (
    SELECT COALESCE(oc.fac_sin_iva, 0)
    FROM orden_de_compra oc 
    WHERE oc.id = orden_de_pago.orden_compra
)
WHERE orden_de_pago.orden_compra IS NOT NULL;

-- Verificar los cambios
SELECT 
    COUNT(*) as total_registros,
    COUNT(CASE WHEN fac_sin_iva = 1 THEN 1 END) as sin_iva,
    COUNT(CASE WHEN fac_sin_iva = 0 THEN 1 END) as con_iva
FROM orden_de_pago;
