-- Verificar y crear las tablas necesarias para el módulo de usuarios

-- 1. Verificar tabla usuarios
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'usuarios' 
ORDER BY ordinal_position;

-- 2. Verificar tabla modulos
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'modulos' 
ORDER BY ordinal_position;

-- 3. Verificar tabla usuario_modulo
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'usuario_modulo' 
ORDER BY ordinal_position;

-- 4. Crear tabla modulos si no existe
CREATE TABLE IF NOT EXISTS modulos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Crear tabla usuario_modulo si no existe
CREATE TABLE IF NOT EXISTS usuario_modulo (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
    modulo_id INTEGER REFERENCES modulos(id) ON DELETE CASCADE,
    fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(usuario_id, modulo_id)
);

-- 6. Insertar módulos básicos si no existen
INSERT INTO modulos (nombre, descripcion) VALUES
('estado_presupuesto', 'Gestión de estado de presupuestos'),
('ingresos', 'Gestión de ingresos y facturas'),
('materiales', 'Gestión de materiales'),
('proveedores', 'Gestión de proveedores'),
('trabajadores', 'Gestión de trabajadores'),
('usuarios', 'Gestión de usuarios'),
('proyectos', 'Gestión de proyectos'),
('presupuesto', 'Gestión de presupuestos'),
('orden_de_compra', 'Órdenes de compra'),
('orden_de_pago', 'Órdenes de pago'),
('orden_pago_pendientes', 'Órdenes de pago pendientes'),
('pagos', 'Gestión de pagos'),
('gastos_directos', 'Gestión de gastos directos'),
('items', 'Gestión de items')
ON CONFLICT (nombre) DO NOTHING;

-- 7. Verificar datos insertados
SELECT COUNT(*) as total_modulos FROM modulos;
SELECT COUNT(*) as total_usuarios FROM usuarios;
SELECT COUNT(*) as total_asignaciones FROM usuario_modulo;
