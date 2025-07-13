-- Agregar columna password_temporal a la tabla usuarios
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS password_temporal BOOLEAN DEFAULT FALSE;

-- Actualizar registros existentes para que tengan password_temporal = false por defecto
UPDATE usuarios SET password_temporal = FALSE WHERE password_temporal IS NULL;

-- Verificar que la columna se agregó correctamente
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'usuarios' AND column_name = 'password_temporal';
