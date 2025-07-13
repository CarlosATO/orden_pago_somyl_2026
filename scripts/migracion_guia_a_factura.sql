-- ==============================================
-- MIGRACIÓN DE DATOS: GUIA_RECEPCION A FACTURA
-- ==============================================
-- Este script copia los datos de la columna guia_recepcion 
-- a la columna factura en la tabla ingresos
-- Solo para registros con orden_compra >= 3246
-- ==============================================

-- Verificar datos antes de la migración
SELECT 
    'ANTES DE LA MIGRACIÓN' as estado,
    COUNT(*) as total_registros,
    COUNT(CASE WHEN guia_recepcion IS NOT NULL THEN 1 END) as con_guia_recepcion,
    COUNT(CASE WHEN factura IS NOT NULL THEN 1 END) as con_factura,
    COUNT(CASE WHEN orden_compra >= 3246 THEN 1 END) as orden_compra_mayor_3246
FROM ingresos;

-- Mostrar registros específicos que serán afectados
SELECT 
    'REGISTROS A MIGRAR' as info,
    id,
    orden_compra,
    guia_recepcion,
    factura,
    CASE 
        WHEN guia_recepcion IS NOT NULL AND factura IS NULL THEN 'SE COPIARÁ'
        WHEN guia_recepcion IS NOT NULL AND factura IS NOT NULL THEN 'YA TIENE FACTURA'
        WHEN guia_recepcion IS NULL THEN 'SIN GUÍA'
        ELSE 'OTRO'
    END as accion
FROM ingresos 
WHERE orden_compra >= 3246
ORDER BY orden_compra, id;

-- ==============================================
-- MIGRACIÓN DE DATOS
-- ==============================================

-- Copiar datos de guia_recepcion a factura
-- Solo para registros con orden_compra >= 3246
-- Solo si factura está vacía (para no sobrescribir datos existentes)
UPDATE ingresos 
SET factura = guia_recepcion
WHERE orden_compra >= 3246 
  AND guia_recepcion IS NOT NULL 
  AND (factura IS NULL OR factura = '');

-- Obtener el número de registros actualizados
SELECT 
    'RESULTADO DE LA MIGRACIÓN' as estado,
    COUNT(*) as registros_actualizados
FROM ingresos 
WHERE orden_compra >= 3246 
  AND factura IS NOT NULL 
  AND factura != '';

-- ==============================================
-- VERIFICAR RESULTADOS DESPUÉS DE LA MIGRACIÓN
-- ==============================================

-- Estadísticas después de la migración
SELECT 
    'DESPUÉS DE LA MIGRACIÓN' as estado,
    COUNT(*) as total_registros,
    COUNT(CASE WHEN guia_recepcion IS NOT NULL THEN 1 END) as con_guia_recepcion,
    COUNT(CASE WHEN factura IS NOT NULL THEN 1 END) as con_factura,
    COUNT(CASE WHEN orden_compra >= 3246 THEN 1 END) as orden_compra_mayor_3246,
    COUNT(CASE WHEN orden_compra >= 3246 AND factura IS NOT NULL THEN 1 END) as migrados_con_factura
FROM ingresos;

-- Mostrar algunos ejemplos de registros migrados
SELECT 
    'EJEMPLOS DE REGISTROS MIGRADOS' as info,
    id,
    orden_compra,
    guia_recepcion,
    factura,
    CASE 
        WHEN guia_recepcion = factura THEN 'MIGRADO CORRECTAMENTE'
        ELSE 'VERIFICAR'
    END as estado_migracion
FROM ingresos 
WHERE orden_compra >= 3246 
  AND factura IS NOT NULL
ORDER BY orden_compra, id
LIMIT 20;

-- Verificar si hay registros con problemas
SELECT 
    'REGISTROS CON POSIBLES PROBLEMAS' as info,
    id,
    orden_compra,
    guia_recepcion,
    factura,
    'FACTURA DIFERENTE A GUÍA' as problema
FROM ingresos 
WHERE orden_compra >= 3246 
  AND guia_recepcion IS NOT NULL 
  AND factura IS NOT NULL
  AND guia_recepcion != factura;

-- ==============================================
-- RESUMEN FINAL
-- ==============================================

-- Resumen de la migración
SELECT 
    '=== RESUMEN DE LA MIGRACIÓN ===' as resumen,
    (SELECT COUNT(*) FROM ingresos WHERE orden_compra >= 3246) as total_registros_candidatos,
    (SELECT COUNT(*) FROM ingresos WHERE orden_compra >= 3246 AND guia_recepcion IS NOT NULL) as registros_con_guia,
    (SELECT COUNT(*) FROM ingresos WHERE orden_compra >= 3246 AND factura IS NOT NULL) as registros_con_factura_final,
    (SELECT COUNT(*) FROM ingresos WHERE orden_compra >= 3246 AND guia_recepcion = factura) as registros_migrados_correctamente;

-- ==============================================
-- NOTAS IMPORTANTES
-- ==============================================

/*
ESTE SCRIPT:

✅ COPIA datos de guia_recepcion a factura
✅ SOLO para registros con orden_compra >= 3246
✅ NO sobrescribe facturas existentes
✅ VERIFICA los resultados antes y después
✅ MUESTRA ejemplos de registros migrados
✅ DETECTA posibles problemas

CONDICIONES DE SEGURIDAD:
- Solo actualiza si factura está vacía (IS NULL OR = '')
- Solo actualiza si guia_recepcion tiene datos
- Solo actualiza registros con orden_compra >= 3246
- Incluye verificaciones múltiples

ANTES DE EJECUTAR:
1. Revisa las consultas SELECT para ver qué datos serán afectados
2. Confirma que los registros mostrados son los correctos
3. Ejecuta el script completo

DESPUÉS DE EJECUTAR:
1. Revisa el resumen final
2. Verifica los ejemplos de registros migrados
3. Comprueba si hay registros con problemas
*/
