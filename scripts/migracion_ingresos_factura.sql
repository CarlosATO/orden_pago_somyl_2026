-- ==============================================
-- SCRIPT DE MIGRACIÓN PARA INGRESOS
-- ==============================================
-- Este script migra los datos de guia_recepcion a factura
-- para corregir el flujo de órdenes de pago
-- ==============================================

-- 1. Verificar el estado actual de los datos
SELECT 
    COUNT(*) as total_ingresos,
    COUNT(CASE WHEN factura IS NOT NULL AND factura != '' THEN 1 END) as con_factura,
    COUNT(CASE WHEN guia_recepcion IS NOT NULL AND guia_recepcion != '' THEN 1 END) as con_guia_recepcion
FROM ingresos;

-- 2. Migrar datos de guia_recepcion a factura SOLO donde factura esté vacía
-- Esto mantiene la integridad de los datos existentes
UPDATE ingresos 
SET factura = guia_recepcion
WHERE 
    (factura IS NULL OR factura = '') 
    AND guia_recepcion IS NOT NULL 
    AND guia_recepcion != '';

-- 3. Opcional: Limpiar guia_recepcion donde se movió a factura
-- (Solo si quieres separar completamente los conceptos)
-- DESCOMENTA las siguientes líneas si quieres hacer esto:
/*
UPDATE ingresos 
SET guia_recepcion = NULL
WHERE 
    factura IS NOT NULL 
    AND factura != ''
    AND factura = guia_recepcion;
*/

-- 4. Verificar el resultado de la migración
SELECT 
    COUNT(*) as total_ingresos_despues,
    COUNT(CASE WHEN factura IS NOT NULL AND factura != '' THEN 1 END) as con_factura_despues,
    COUNT(CASE WHEN guia_recepcion IS NOT NULL AND guia_recepcion != '' THEN 1 END) as con_guia_recepcion_despues
FROM ingresos;

-- 5. Mostrar algunos ejemplos del resultado
SELECT 
    id,
    orden_compra,
    factura,
    guia_recepcion,
    fecha,
    proveedor
FROM ingresos 
WHERE factura IS NOT NULL 
ORDER BY id DESC 
LIMIT 10;

-- ==============================================
-- NOTAS IMPORTANTES
-- ==============================================

/*
PROPÓSITO:
- Corregir el flujo de datos entre ingresos y órdenes de pago
- Factura: Campo principal para el documento (obligatorio)
- Guía de recepción: Campo opcional para control interno

SEGURIDAD:
- Solo actualiza registros donde factura esté vacía
- No sobrescribe datos existentes en factura
- Mantiene guia_recepcion para referencia

IMPACTO:
- Mejora la consistencia de datos
- Permite que las órdenes de pago funcionen correctamente
- Separa conceptos de factura y guía de recepción

REVERSIÓN:
Si necesitas deshacer los cambios, puedes usar:
UPDATE ingresos SET factura = NULL WHERE factura = guia_recepcion;
*/
