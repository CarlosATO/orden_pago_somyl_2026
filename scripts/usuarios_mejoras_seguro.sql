-- ==============================================
-- SCRIPT SEGURO - SOLO AGREGAR COLUMNAS
-- ==============================================
-- Este script solo agrega las nuevas columnas sin 
-- operaciones que Supabase considere "destructivas"
-- ==============================================

-- 1. Agregar columna 'activo' para activar/desactivar usuarios
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT true;

-- 2. Agregar columna 'bloqueado' para bloquear temporalmente usuarios
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS bloqueado BOOLEAN DEFAULT false;

-- 3. Agregar columna 'intentos_fallidos' para control de seguridad
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS intentos_fallidos INTEGER DEFAULT 0;

-- 4. Agregar columna 'fecha_ultimo_acceso' para tracking de actividad
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS fecha_ultimo_acceso TIMESTAMP WITH TIME ZONE;

-- 5. Agregar columna 'fecha_creacion' para auditoría
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- 6. Agregar columna 'fecha_actualizacion' para auditoría
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS fecha_actualizacion TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- 7. Agregar columna 'motivo_bloqueo' para documentar razones de bloqueo
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS motivo_bloqueo TEXT;

-- 8. Agregar columna 'bloqueado_por' para auditoría de quien bloquea
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS bloqueado_por INTEGER REFERENCES usuarios(id);

-- 9. Agregar columna 'fecha_bloqueo' para control temporal
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS fecha_bloqueo TIMESTAMP WITH TIME ZONE;

-- ==============================================
-- ÍNDICES PARA MEJORAR PERFORMANCE
-- ==============================================

-- Índice para búsquedas por estado activo
CREATE INDEX IF NOT EXISTS idx_usuarios_activo 
ON usuarios(activo);

-- Índice para búsquedas por estado bloqueado
CREATE INDEX IF NOT EXISTS idx_usuarios_bloqueado 
ON usuarios(bloqueado);

-- Índice para búsquedas por email (para login)
CREATE INDEX IF NOT EXISTS idx_usuarios_email 
ON usuarios(email);

-- Índice para fecha de último acceso
CREATE INDEX IF NOT EXISTS idx_usuarios_ultimo_acceso 
ON usuarios(fecha_ultimo_acceso);

-- ==============================================
-- VERIFICAR RESULTADOS
-- ==============================================

-- Consulta para verificar la estructura actualizada
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'usuarios' 
ORDER BY ordinal_position;
