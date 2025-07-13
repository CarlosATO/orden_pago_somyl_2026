-- ==============================================
-- SCRIPT DE MEJORAS PARA TABLA DE USUARIOS
-- ==============================================
-- Este script agrega las nuevas columnas necesarias para 
-- el sistema de gestión de usuarios mejorado
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
-- ACTUALIZAR USUARIOS EXISTENTES
-- ==============================================

-- Actualizar usuarios existentes con valores por defecto
UPDATE usuarios 
SET 
    activo = true,
    bloqueado = false,
    intentos_fallidos = 0,
    fecha_creacion = NOW(),
    fecha_actualizacion = NOW()
WHERE activo IS NULL OR bloqueado IS NULL;

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
-- TRIGGER PARA ACTUALIZAR FECHA_ACTUALIZACION
-- ==============================================

-- Función para actualizar fecha_actualizacion automáticamente
CREATE OR REPLACE FUNCTION actualizar_fecha_actualizacion()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger que se ejecuta antes de cada UPDATE
DROP TRIGGER IF EXISTS trigger_usuarios_actualizacion ON usuarios;
CREATE TRIGGER trigger_usuarios_actualizacion
    BEFORE UPDATE ON usuarios
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_fecha_actualizacion();

-- ==============================================
-- COMENTARIOS EN LAS COLUMNAS
-- ==============================================

COMMENT ON COLUMN usuarios.activo IS 'Indica si el usuario está activo en el sistema';
COMMENT ON COLUMN usuarios.bloqueado IS 'Indica si el usuario está temporalmente bloqueado';
COMMENT ON COLUMN usuarios.intentos_fallidos IS 'Número de intentos fallidos de login';
COMMENT ON COLUMN usuarios.fecha_ultimo_acceso IS 'Fecha y hora del último acceso del usuario';
COMMENT ON COLUMN usuarios.fecha_creacion IS 'Fecha y hora de creación del usuario';
COMMENT ON COLUMN usuarios.fecha_actualizacion IS 'Fecha y hora de última actualización';
COMMENT ON COLUMN usuarios.motivo_bloqueo IS 'Razón por la cual el usuario fue bloqueado';
COMMENT ON COLUMN usuarios.bloqueado_por IS 'ID del usuario que realizó el bloqueo';
COMMENT ON COLUMN usuarios.fecha_bloqueo IS 'Fecha y hora del bloqueo';

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

-- Consulta para verificar los usuarios existentes
SELECT 
    id,
    nombre,
    email,
    activo,
    bloqueado,
    intentos_fallidos,
    fecha_creacion,
    fecha_ultimo_acceso
FROM usuarios;

-- ==============================================
-- NOTAS IMPORTANTES
-- ==============================================

/*
INSTRUCCIONES PARA EJECUTAR:

1. Conectarte a tu panel de Supabase
2. Ir a la sección "SQL Editor"
3. Crear una nueva consulta
4. Pegar este código completo
5. Ejecutar el script

FUNCIONALIDADES AGREGADAS:

✅ activo: Control de usuarios activos/inactivos
✅ bloqueado: Bloqueo temporal de usuarios
✅ intentos_fallidos: Control de seguridad
✅ fecha_ultimo_acceso: Tracking de actividad
✅ fecha_creacion: Auditoría de creación
✅ fecha_actualizacion: Auditoría de cambios
✅ motivo_bloqueo: Documentación de bloqueos
✅ bloqueado_por: Auditoría de quien bloquea
✅ fecha_bloqueo: Control temporal de bloqueos

COMPATIBILIDAD:
- Usa IF NOT EXISTS para evitar errores si ya existen
- Valores por defecto para no afectar usuarios existentes
- Índices para mejorar performance
- Triggers para automatizar fechas

SEGURIDAD:
- No afecta el funcionamiento actual
- Mantiene la integridad referencial
- Valores por defecto seguros
*/
