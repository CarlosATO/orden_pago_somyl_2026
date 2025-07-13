-- Script para agregar columna factura a la tabla orden_de_compra
-- Ejecutar este script en Supabase SQL Editor si se desea usar la columna factura

ALTER TABLE orden_de_compra 
ADD COLUMN IF NOT EXISTS factura TEXT DEFAULT '';

-- Agregar comentario para documentar el propósito de la columna
COMMENT ON COLUMN orden_de_compra.factura IS 'Número de factura asociada a la orden de compra';

-- Crear índice para mejorar las consultas por factura
CREATE INDEX IF NOT EXISTS idx_orden_compra_factura ON orden_de_compra(factura);
