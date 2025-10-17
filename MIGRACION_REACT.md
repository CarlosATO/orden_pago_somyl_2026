# MIGRACIÓN FRONTEND A REACT

## Objetivo
Migrar el frontend del sistema de gestión de compras y pagos SOMYL desde HTML/Jinja (Flask) a React, para mejorar la velocidad, experiencia de usuario y mantenibilidad.

## Plan General
1. **Analizar las vistas y funcionalidades actuales**
2. **Crear la estructura inicial del proyecto React**
3. **Migrar cada vista a componentes React**
4. **Conectar el frontend React con el backend Python (Flask)**
5. **Probar y ajustar cada módulo migrado**

## Estado Actual
- Backup del sistema realizado y subido a la nueva repo: `orden_pago_somyl_2026`
- Variables de entorno configuradas y sistema funcionando localmente
- Listo para iniciar la migración del frontend

---

## Avances
**Integración de React Router y ruta de login:**
	- Archivo: frontend/src/App.js
	- Se agregó React Router con rutas para `/login` y `/usuarios`.
	- El componente de login está accesible en `/login` y el de usuarios en `/usuarios`.
**Componente de login creado en React:**
	- Archivo: frontend/src/login/Login.js
	- Permite autenticación de usuarios contra el backend Flask.
	- Envía credenciales y gestiona el estado de error.
	- Listo para integrar en la navegación y probar el acceso a módulos protegidos.
	- Nota: `Login.js` fue renombrado a `Login.jsx` para cumplir con los requisitos de Vite y JSX.

Resumen de la sesión — Migración frontend a React (17/10/2025)

Qué hicimos (acciones concretas):

- Creación de un backup y nuevo repo: `CarlosATO/orden_pago_somyl_2026`.
- Levantamos el proyecto localmente y configuramos variables de entorno.
- Creación del frontend con Vite en `frontend/`.
- Estructura de módulos en `frontend/src/`:
  - `usuarios/`, `login/`, `ordenes/`, `pagos/`, `proveedores/`, `presupuestos/`, `materiales/`, `components/`.
- Se creó un script raíz `run.py` (ejecutable) para iniciar backend (Flask) y frontend (Vite) con un solo comando.
- Se añadió un endpoint JSON en el backend: `/usuarios/api/listado` (en `app/modules/usuarios.py`).
- En el frontend:
  - Integración de React Router (`frontend/src/App.jsx`).
  - Componentes básicos creados:
    - `frontend/src/login/Login.jsx` (formulario de login que hace POST a `/auth/login`).
    - `frontend/src/usuarios/Usuarios.jsx` (consulta `GET /usuarios/api/listado`).
    - Placeholders: `UsuariosTable.js`, `UsuariosForm.js`.
  - Renombrado de archivos con JSX a la extensión `.jsx` para evitar errores con Vite.
- Documentación básica actualizada: `MIGRACION_REACT.md` y este archivo resumen `MIGRACION_SUMMARY.md`.

Cómo ejecutar (rápido):

1) Dar permiso al script (solo la primera vez):

```bash
chmod +x run.py
```

2) Iniciar ambos servidores (desde la raíz del proyecto):

```bash
run.py
# ó
./run.py
```

- Frontend Vite disponible en: http://localhost:5175 (puede cambiar si 5173/5174 ocupados)
- Backend Flask disponible en: http://localhost:5006

Si prefieres hacerlo manual:

```bash
# Backend
cd seguimiento_ordenes
python run.py

# Frontend (otra terminal)
cd frontend
npm run dev
```

Notas y problemas detectados y resueltos:

- Vite exige extensión `.jsx` para archivos que usan JSX. Se renombraron `App.jsx`, `Login.jsx`, `Usuarios.jsx` y se eliminaron versiones conflictivas `.js`.
- Inicialmente la app mostraba la página por defecto de Vite porque `App.jsx` no era la entrada; se corrigió `main.jsx` para importar `App.jsx`.
- Si algún puerto está en uso, `run.py` o Vite pueden elegir puertos alternativos (Vite intentará 5173, 5174, 5175...). Flask fallará si el puerto está ocupado.

Próximos pasos (priorizados):

1. Completar el flujo de login:
   - Enviar credenciales desde `Login.jsx` a `/auth/login`.
   - El backend debe establecer la sesión/cookie de usuario.
   - Redirigir al frontend a `/usuarios` tras login exitoso.
2. Implementar `UsuariosTable` con columnas, filtros y paginación mínima.
3. Proteger rutas en React (redirigir a `/login` si no autenticado).
4. Migrar otras vistas por prioridad (órdenes, pagos, proveedores...).

Si quieres, empiezo ahora por implementar el punto 1 (login completo + redirección). Indícame si quieres que:
- use cookies/sesión como en el backend actual (recomendado), o
- use JWT (requiere cambio en backend).


**Ejecución simplificada del sistema:**
	- Se creó un script ejecutable `run.py` en la raíz del proyecto para iniciar backend y frontend con un solo comando.
	- Se configuró un alias en `~/.zshrc` para que al escribir `run.py` en la terminal, ambos servidores se inicien automáticamente.
	- Acceso al sistema:
			- Frontend: http://localhost:5175
			- Backend: http://localhost:5006
	- Solo es necesario abrir la terminal y escribir `run.py` para comenzar a trabajar.


**17/10/2025**
- Proyecto documentado y respaldado
- Plan de migración definido
- Estructura inicial de React creada en la carpeta `frontend` usando Vite
- Proyecto React probado exitosamente en `localhost:5175` (pantalla Vite + React visible)
- Listo para comenzar la migración de vistas y componentes

**Estructura de carpetas creada para los módulos principales:**
	- frontend/src/usuarios
	- frontend/src/login
	- frontend/src/ordenes
	- frontend/src/pagos
	- frontend/src/proveedores
	- frontend/src/presupuestos
	- frontend/src/materiales
	- frontend/src/components
Las carpetas están listas para organizar los componentes y vistas de cada módulo.

**Archivos base creados para el módulo de usuarios:**
	- frontend/src/usuarios/Usuarios.js
	- frontend/src/usuarios/UsuariosTable.js
	- frontend/src/usuarios/UsuariosForm.js
Estos archivos servirán como punto de partida para migrar la lógica y vistas del sistema de usuarios.

**Conexión establecida entre frontend y backend para usuarios:**
	- Endpoint `/usuarios/api/listado` creado en Flask para devolver la lista de usuarios en formato JSON.
	- Componente `Usuarios.js` consulta el endpoint y muestra los datos en el frontend.
	- Listo para probar ambos servidores localmente y visualizar los usuarios desde React.

---

## Siguiente paso
Crear carpeta y proyecto React en la raíz del repositorio.

---

*Este archivo se irá actualizando con cada avance y decisión tomada en la migración.*

## Detalle técnico y pasos de verificación

Este apartado describe con detalle las modificaciones realizadas, cómo probar el flujo de login localmente, los archivos afectados, problemas detectados y los siguientes pasos recomendados.

1) Cambios principales realizados
- Backend (Flask)
	- Habilitado CORS para permitir peticiones desde el dev server de Vite y aceptar credenciales (cookies): archivo `app/__init__.py`.
	- Re-registrado el blueprint de autenticación con prefijo `/auth` para que el endpoint de login coincida con las llamadas del frontend.
	- Modificado el verificador de contraseñas en `app/modules/auth.py` para detectar hashes con prefijo `scrypt:` y, cuando sea posible, usar `passlib` para verificarlos. Existe un fallback a los métodos anteriores si `passlib` no está instalado.
	- Añadido un endpoint JSON para listar usuarios: `GET /usuarios/api/listado` (archivo `app/modules/usuarios.py`).

- Frontend (React + Vite)
	- Proyecto Vite creado en `frontend/` con React.
	- Rutas básicas configuradas en `frontend/src/App.jsx` y `frontend/src/main.jsx`.
	- Componente `Login.jsx` en `frontend/src/login/Login.jsx` que envía un POST a `http://localhost:5006/auth/login` con `credentials: 'include'` y maneja errores/redirects.
	- Componente `Usuarios.jsx` en `frontend/src/usuarios/Usuarios.jsx` que consume `GET http://localhost:5006/usuarios/api/listado` y muestra los datos (placeholder/table).
	- Archivos renombrados a `.jsx` para evitar problemas con Vite (por ejemplo, `Login.jsx`, `App.jsx`, `Usuarios.jsx`).

2) Cómo reproducir y probar localmente el login (rápido)

- Prerrequisitos
	- Copia `.env.example` a `.env` y completa los valores si todavía no lo hiciste.
	- Asegúrate de que las dependencias Python están instaladas. Para que la verificación de hashes scrypt funcione, instala `passlib`:

```bash
pip install passlib
```

	- En el entorno Node, desde `frontend/` instala dependencias si no lo hiciste:

```bash
cd frontend
npm install
```

- Iniciar servidores

```bash
# Desde la raíz del repositorio (solo la primera vez hacer chmod +x run.py)
./run.py

# O por separado:
# Backend
python run.py
# Frontend (otra terminal)
cd frontend
npm run dev
```

- Flujo de prueba
	1. Abrir el navegador en `http://localhost:5175/login`.
	2. Introducir las credenciales de prueba (por ejemplo: email `carlosalegria@me.com`, contraseña `camilo`) y enviar.
	3. En el backend revisa la consola/terminal donde corre Flask: debe imprimir intentos de login y mensajes de verificación.
	4. Verificar en las DevTools del navegador (Network tab) que la llamada POST a `http://localhost:5006/auth/login` responde con un status 200 y que la cookie de sesión está presente en la respuesta (si el backend la establece).
	5. Tras login exitoso, el frontend espera un JSON con campo `redirect`; en tal caso redirige a `/usuarios`.

3) Archivos modificados / creados (lista precisa)

- Archivos del backend
	- `app/__init__.py` — configuración CORS y registro de blueprints.
	- `app/modules/auth.py` — verificación de contraseñas, manejo de login vía JSON.
	- `app/modules/usuarios.py` — endpoint `GET /usuarios/api/listado`.

- Archivos del frontend
	- `frontend/package.json` — dependencias y scripts (creado por Vite).
	- `frontend/src/main.jsx` — entrada de React.
	- `frontend/src/App.jsx` — rutas y layout básico.
	- `frontend/src/login/Login.jsx` — formulario y lógica de login.
	- `frontend/src/login/Login.css` — estilos del formulario de login.
	- `frontend/src/usuarios/Usuarios.jsx` — consumidor del endpoint de usuarios.

4) Problemas conocidos y soluciones/mitigaciones

- Passlib no instalado: la base de datos contiene hashes `scrypt:` que requieren `passlib` para su verificación. Si no se instala, el backend intentará otros métodos y el login fallará para esos usuarios.
	- Solución: Instalar `passlib` en el entorno Python y añadirlo a `requirements.txt`.

- Conflictos de puerto: Flask usa por defecto `5006` en este proyecto; si está en uso, Flask fallará. Vite intentará puertos 5173->5175 automáticamente.
	- Solución: liberar el puerto o cambiar la configuración de Flask en `run.py` o `app.run()`.

- SeaSurf y compatibilidad con Flask 3.x: Si ves errores relacionados con SeaSurf al arrancar, es posiblemente por incompatibilidad con Flask 3.x.
	- Mitigación: SeaSurf es opcional — el arranque del backend funciona sin él; revisar logs y eliminar/ajustar la extensión en `app/__init__.py` si fuera necesario.

- CORS y cookies: asegúrate de que `flask_cors.CORS` se configuró con `supports_credentials=True` y que el frontend hace fetch con `credentials: 'include'`.

5) Siguientes pasos y recomendaciones (priorizados)

- Inmediatos (alta prioridad)
	1. Instalar `passlib` y reiniciar el backend para que la verificación de hashes scrypt funcione correctamente.
	2. Reproducir login con las credenciales de prueba y confirmar que la respuesta incluye la cookie de sesión.

- Mediano plazo
	3. Implementar en el backend un endpoint que devuelva el usuario actual (`GET /auth/whoami`) para que el frontend pueda comprobar el estado de sesión y proteger rutas.
	4. Implementar protección de rutas en React (redirect a `/login` si no autenticado) usando un contexto de Auth o un hook `useAuth`.

- Opcional (si se desea cambiar arquitectura)
	5. Migrar a JWT si prefieres tokens en vez de sesión/cookie (requiere cambios en backend y mayor esfuerzo en seguridad y revocación).

6) Notas para commit y despliegue

- No incluyas tu `.env` en el repo. Añade/actualiza `requirements.txt` con `passlib` antes de desplegar.
- Antes de desplegar en Railway u otro hosting, verifica que la versión de Flask y las extensiones (SeaSurf) son compatibles entre sí.

---

Si quieres, hago ahora la instalación de `passlib` en el entorno virtual del proyecto y reinicio el backend para verificar el flujo de login; dime si quieres que lo haga y si quieres que añada `passlib` a `requirements.txt` automáticamente.
