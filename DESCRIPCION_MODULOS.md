# Resumen de Módulos de Nexus Somyl

Este documento resume la función principal de cada archivo `.py` que compone la aplicación.

## Módulos de Parámetros (Configuración Base)
Estos módulos se encargan de gestionar la información maestra que alimenta el resto del sistema.

### proveedores.py
- **Propósito:** Administra el alta, baja y modificación (CRUD) de los proveedores.
- **Funciones Clave:** Valida el RUT chileno, normaliza los datos (mayúsculas, minúsculas) y evita la creación de proveedores con RUT duplicado.

### materiales.py
- **Propósito:** Gestiona el catálogo de productos y servicios.
- **Funciones Clave:** Permite crear y editar materiales, asignándoles un código, descripción, tipo e ítem. Evita códigos duplicados.

### items.py
- **Propósito:** Administra las categorías o familias principales de los materiales (Ej: "HERRAMIENTAS", "ARRIENDOS").
- **Funciones Clave:** Permite crear y editar estas categorías para mantener la clasificación organizada.

### proyectos.py
- **Propósito:** Gestiona los proyectos o centros de costo de la empresa.
- **Funciones Clave:** Permite crear y editar proyectos, asociándoles opcionalmente un monto de venta y observaciones.

### trabajadores.py
- **Propósito:** Administra la lista de empleados de la empresa.
- **Funciones Clave:** Permite crear y editar los datos de los trabajadores, que luego se usarán para identificar quién solicita una compra o autoriza un pago.

## Módulos Operativos (Flujo de Compras y Pagos)
Estos módulos gestionan el ciclo de vida de una adquisición.

### ordenes.py
- **Propósito:** Es el corazón de las compras. Se encarga de crear las Órdenes de Compra (OC).
- **Funciones Clave:** Genera un número de OC correlativo, permite añadir múltiples líneas de materiales, calcula totales (con o sin IVA) y genera un PDF profesional de la OC.

### ingresos.py
- **Propósito:** Registra la recepción de mercancía o servicios basados en una OC existente.
- **Funciones Clave:** Permite buscar una OC, registrar cantidades recibidas (parcial o totalmente) y asociar un número de factura o guía de despacho. Incluye una opción para marcar ingresos con "Factura Pendiente".

### ordenes_pago.py / ordenes_pago_create.py
- **Propósito:** Gestiona la creación de Órdenes de Pago (OP) a partir de los ingresos registrados.
- **Funciones Clave:** Busca ingresos por proveedor, agrupa los materiales por documento (factura/guía), permite al usuario seleccionar qué ingresos pagar y genera la OP con un número correlativo.

### ordenes_pago_pendientes.py
- **Propósito:** Módulo específico para regularizar los ingresos que se marcaron como "Factura Pendiente".
- **Funciones Clave:** Muestra una lista de todos los ingresos sin factura, permitiendo al usuario asignarles el número de documento correspondiente una vez que llega.

## Módulos de Presupuesto y Finanzas
Estos módulos se enfocan en el control de costos y el análisis financiero.

### presupuestos.py
- **Propósito:** Permite la planificación de costos por proyecto e ítem.
- **Funciones Clave:** Permite ingresar montos presupuestados de forma manual o a través de la importación masiva desde una plantilla de Excel.

### gastos_directos.py
- **Propósito:** Registra gastos que no pasan por el flujo de Orden de Compra (ej. sueldos, servicios básicos).
- **Funciones Clave:** Permite asociar gastos directamente a un proyecto y a un ítem para un mes específico.

### pagos.py
- **Propósito:** Es el informe final del ciclo de pagos.
- **Funciones Clave:** Muestra un listado de todas las Órdenes de Pago, permite registrar la fecha efectiva en que se pagó cada una, filtra la información y la exporta a Excel.

### estado_presupuesto.py
- **Propósito:** Es el módulo de Business Intelligence. Compara lo presupuestado contra lo gastado.
- **Funciones Clave:** Genera una tabla dinámica que cruza proyectos e ítems con los meses, mostrando en cada celda el monto "Presupuestado" vs. el "Real" (la suma de Órdenes de Pago y Gastos Directos). Permite filtrar por proyecto y rango de fechas.

## Módulo de Administración

### usuarios.py
- **Propósito:** Gestiona la seguridad y el acceso al sistema.
- **Funciones Clave:** Permite crear, editar y administrar usuarios. Asigna permisos específicos a cada usuario para que solo puedan acceder a los módulos que les corresponden. También maneja el bloqueo de cuentas y el reseteo de contraseñas.
