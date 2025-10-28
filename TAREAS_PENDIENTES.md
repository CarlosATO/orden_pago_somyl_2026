++ /Users/carlosalegria/Desktop/Migracion_OP/TAREAS_PENDIENTES.md
# TAREAS PENDIENTES (pagos)

Este archivo documenta el problema detectado en el módulo `pagos`, las observaciones del diagnóstico y las soluciones propuestas. Útil para quien retome la tarea.

## Resumen del problema

- Sintoma: al filtrar en la UI por "Con Abonos" (o por estados similares) la tabla detallada muestra solo 2 filas en vez de las 4 filas esperadas (por ejemplo, faltaban filas con abonos parciales en la vista filtrada).
- Observación: En llamadas directas a la API desde terminal con `estado=abono` y `per_page=1000`, las órdenes estaban presentes y clasificadas correctamente (3188 pagada, 3144 y 3126 como abono). El comportamiento inconsistente ocurre al usar la UI.

## Diagnóstico realizado

1. Alineación de lógica:
   - Reescribí `get_stats` para usar batching y agrupación por `orden_numero`, y para computar `total_pago`, `total_abonado` y `saldo` de forma equivalente a `list_pagos`.
2. Precisión monetaria:
   - Convertí sumas a enteros redondeados (`int(round(...))`) para eliminar residuos por precisión float que provocaban saldos residuales y clasificaciones erróneas.
3. Estado y priorización:
   - Ajusté `calcular_estado_pago` para priorizar `abono` cuando hay abonos parciales y queda saldo > 0.
4. Normalización del filtro `estado`:
   - Añadí mapeo básico en `list_pagos` que convierte etiquetas UI comunes (ej. `Con Abonos`) en valores internos (`abono`).

Pese a estos cambios, la UI sigue mostrando un número reducido de filas al aplicar el filtro. Esto indica que la causa puede estar del lado del frontend o en la forma exacta del query param que envía la UI.

## Posibles causas

1. Frontend envía un valor distinto en `estado` (p. ej. mayúsculas, espacio, slug diferido o localización) que no casaba exactamente con el filtro del backend.
2. El frontend realiza filtrado adicional en el cliente después de recibir los datos (por ejemplo, filtra por proyecto, fecha o hace un map que excluye filas).
3. Paginación del frontend: el `per_page` por defecto en la UI puede ser 50 y la orden esperada aparece en otra página (aunque el síntoma sugiere que faltan filas concretas, no solo paginación).
4. El frontend aplica múltiples filtros simultáneos (proyecto, fecha, proveedor) que reducen los resultados; el usuario puede estar viendo una combinación de filtros.
5. Problema en el control del estado en el frontend: el selector visual muestra "Con Abonos" pero envía otro parámetro (por ejemplo `with_abonos=true` o `con_abonos`) que no coincide con el esperado.

## Acciones propuestas (priorizadas)

Prioridad alta

- (A) Capturar exactamente qué envía el frontend: añadir logging temporal en `list_pagos` que registre `request.args.get('estado')` y otros filtros cuando se active desde la UI. Reproducir desde el navegador y revisar logs.
  - Pros: diagnóstico rápido y sin tocar frontend.
  - Contras: requiere reproducir en entorno con logs visibles.

- (B) Ajustar frontend para enviar siempre los valores internos (`abono`/`pagado`/`pendiente`) en vez de etiquetas human-readable.
  - Pros: Solución limpia y estable a largo plazo.
  - Contras: Requiere toque en frontend y despliegue.

Prioridad media

- (C) Extender y endurecer el mapeo en backend (más alias, normalización unicode, trimming). Ya se implementó un mapeo básico — se puede ampliar.
  - Pros: Rápido de implementar, tolerante.
  - Contras: Backend termina adivinando valores del UI; no corrige la raíz.

- (D) Añadir tests end-to-end que reproduzcan la acción del selector en la UI y verifiquen que la API reciba X y la tabla muestre Y.
  - Pros: Previene regresiones.
  - Contras: Requiere infra de pruebas y tiempo.

Prioridad baja

- (E) Crear una herramienta de diagnóstico en el frontend para mostrar el request que se envía (opción rápida: mostrar en consola del navegador o en UI dev panel).

## Recomendación

1. Implementar (A) inmediatamente: agregar logging temporal en backend para capturar `estado` y los filtros que recibe cuando se usa la UI. Reproducir el escenario en el navegador y copiar los logs.
2. Si (A) demuestra que el frontend envía un valor inesperado, proceder con (B) — corregir el frontend para enviar valores internos. Si el frontend no puede cambiar de inmediato, complementar con (C) — ampliar el mapeo en backend.
3. Escribir un test unitario que valide el cálculo de estado/saldo para el caso donde la suma de abonos == total (ya que fue causante del bug original).

## Materiales / referencias

- Branch actual con cambios: `backup-before-proveedores-change-20251024-130912`
- Archivo principal modificado: `nuevo_proyecto/backend/modules/pagos.py`
- Endpoint diagnóstico: `/api/pagos/stats?debug=1`

---

Si querés, implemento (A) ahora (logging temporal), lo reproducís desde la UI y traés los logs; con eso cerramos la causa raíz y procedemos con (B) o (C) según corresponda.