## Módulo: Órdenes de Compra (Lista, Vista Previa y Navegación a Creación)

Este documento describe el alcance, comportamiento de la interfaz y los endpoints a usar para implementar el módulo UI de "Órdenes de Compra" que se mostrará bajo el menú "Adquisiciones / Órdenes de Compra".

Objetivo
--------
- Mostrar una lista clara y paginada de las Órdenes de Compra emitidas con columnas: Fecha, Nº O.C., Proveedor, Estado, Proyecto y Monto.
- Permitir crear una nueva orden desde un botón "+ Nuevo" en la cabecera.
- Al seleccionar una orden (doble click), abrir la vista previa y navegar al módulo existente de creación/edición de órdenes con los datos de la OC seleccionada.
- Desde la vista previa permitir acciones: Imprimir/Reimprimir PDF, Editar (ir a formulario de órdenes) y botón "Ingreso" que redirija al módulo de Ingreso.

Supuestos y restricciones
-------------------------
- No se modificará la lógica actual del backend `nuevo_proyecto/backend/modules/ordenes.py` (ya existente). Este README asume que los endpoints que expone dicho módulo están disponibles.
- El módulo de creación/edición de órdenes ya existe y es accesible desde el sidebar (ruta a confirmar). El botón "+ Nuevo" y la navegación por doble click deben reutilizar esa ruta.
- La generación de PDF ya está implementada por el backend (hay módulos `pdf/*`). La vista previa usará un endpoint que devuelva el PDF o una URL al PDF.

Campos que se mostrarán en la lista
----------------------------------
- Fecha (fecha de la OC)
- Número O.C. (orden_compra)
- Proveedor (nombre)
- Estado (Pendiente / Recibida / Recepción Parcial / etc.)
- Proyecto (nombre del proyecto)
- Monto (suma total de la OC, formateada como moneda)

Comportamiento UI detallado
--------------------------
1. Página de lista (ruta propuesta: `/adquisiciones/ordenes`)
   - Cabecera con título "Órdenes de compra" y botón "+ Nuevo" a la derecha.
   - Tabla con columnas mencionadas, paginada (ej: 25 por página).
   - Orden por fecha desc por defecto.
   - Filtros opcionales: búsqueda libre (nº OC, proveedor), filtro por estado y por proyecto.
   - Click simple: seleccionar fila (resaltar). Doble click: abrir vista previa y navegar al módulo de edición/visualización con la OC cargada.

2. Botón "+ Nuevo"
   - Al pulsarlo debe redirigir inmediatamente al módulo existente de creación de órdenes (ruta de creación ya implementada). No abrir un modal nuevo.

3. Vista previa / detalle (modal o ruta)
   - Al hacer doble click sobre una orden se abre una vista previa. Implementación recomendada:
     - Modal con pestaña "Detalle" y pestaña "PDF".
     - Pestaña "Detalle": mostrar encabezado de OC (fecha, proveedor, proyecto, solicitante, total) y tabla de líneas con estado de recepción por línea.
     - Pestaña "PDF": iframe que carga el PDF devuelto por backend (endpoint: `GET /api/ordenes/<oc_numero>/pdf` o similar).
   - Botones en la vista previa:
     - "Imprimir" → abrir diálogo de impresión del navegador (sobre iframe o descargar y abrir).
     - "Editar" → navegar a la ruta de edición/visualización del módulo de órdenes (con la OC cargada). Esta navegación debe reutilizar el módulo `ordenes.py` existente.
     - "Ingreso" → redirigir al módulo de Ingreso (ruta a confirmar). No crear automáticamente ingreso; sólo navegar al formulario de ingreso con referencia si aplica.

API / Endpoints (basados en `nuevo_proyecto/backend/modules/ordenes.py`)
------------------------------------------------------------------
- GET /api/ordenes  
  - Devuelve listado resumido (fecha, orden_compra, proveedor, proyecto, total, estado).
- GET /api/ordenes/<oc_numero>  
  - Devuelve detalle completo de la OC (líneas, totales, estado por línea, datos de proveedor/proyecto).
- POST /api/ordenes  
  - Crear nueva OC (ya implementado en `ordenes.py`).
- GET /api/ordenes/<oc_numero>/pdf  (si no existe, usar el endpoint de generación de PDF actual)
  - Devuelve el PDF o una URL para descargarlo.

Integración con rutas existentes
--------------------------------
- La lista debe mostrarse en el enlace de sidebar existente "Adquisiciones / Órdenes de Compra". Si actualmente ese enlace abre directamente el formulario de creación, debemos cambiar la navegación para que abra la lista. El formulario de creación seguirá existiendo y se usará para crear/editar.
- Doble click sobre una fila → navegar al formulario de edición con parámetros (ej: `/adquisiciones/ordenes?oc=12345` o `/adquisiciones/ordenes/editar/12345`). Recomendado usar ruta `/adquisiciones/ordenes/editar/:oc_numero`.

Requisitos y permisos
---------------------
- La lista y las acciones deben requerir token JWT válido (el frontend debe enviar Authorization header). Reutilizar las utilidades de autenticación existentes.
- Mostrar/ocultar botones (Nuevo, Editar) según permisos del usuario (si existen roles). Si no hay roles, mostrar a todos.

Criterios de aceptación
-----------------------
1. Al abrir "Adquisiciones / Órdenes de Compra" se muestra la lista con datos reales provenientes de `GET /api/ordenes`.
2. El botón "+ Nuevo" redirige al módulo de creación existente.
3. Doble click sobre una OC abre la vista previa; desde ahí se puede:
   - Ver el PDF y usar imprimir.
   - Pulsar "Editar" para ir al formulario de edición con datos cargados.
   - Pulsar "Ingreso" para ir al módulo Ingreso.
4. No se realizan envíos de correo ni conversiones a facturas desde este flujo.

Lista de tareas técnicas propuestas (implementación posterior)
-----------------------------------------------------------
1. Frontend
   - Crear `OrdenesCompra.jsx` (lista) y `OrdenPreview.jsx` (modal/preview).
   - Añadir rutas en `frontend/src/App.jsx` y entrada en `Sidebar.jsx`.
   - Consumir `/api/ordenes` y `/api/ordenes/<id>`.
   - Implementar manejo de errores y estados de carga.

2. Backend (si faltara algo)
   - Añadir endpoint `/api/ordenes/<id>/pdf` si no existe y asegurar CORS/proxy.

3. Tests
   - Test de endpoint list y detalle.
   - Test de UI básico: smoke test que la lista carga.

Preguntas pendientes (para ejecutar la implementación)
----------------------------------------------------
1. Ruta exacta del módulo de creación/edición actual (para redirigir desde "+ Nuevo" y "Editar").
2. Ruta exacta del módulo de Ingreso (para redirigir desde el botón "Ingreso").
3. ¿Deseas que la vista previa sea modal o una ruta dedicada? (Recomendado: modal con opción a abrir en nueva pestaña).
4. ¿Hay reglas de permisos específicas para mostrar/ocultar botones?

Notas finales
------------
Este documento sirve como especificación para implementar la interfaz de listado y vista previa de Órdenes de Compra reutilizando el backend existente (`ordenes.py`) y el módulo de creación ya presente. Tras confirmar las rutas de creación/ingreso y las decisiones de UI (modal vs ruta), puedo empezar la implementación por pasos pequeños y verificables.

---
Archivo generado automáticamente el 7 de noviembre de 2025.
