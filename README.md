# 🚀 Sistema de Gestión de Órdenes - Full Stack

Sistema web completo con backend en **Flask**, frontend en **React + Vite**, base de datos **Supabase** y autenticación JWT.

---

## 🆕 Últimas Actualizaciones

### ✅ Módulo de Usuarios Implementado (3 Nov 2025)
Se ha completado la implementación del **módulo de Gestión de Usuarios** con todas las funcionalidades del sistema antiguo:

**Características principales:**
- ✅ CRUD completo de usuarios
- ✅ Gestión de permisos por módulos (tabla `usuario_modulo`)
- ✅ Activación/Desactivación de usuarios
- ✅ Bloqueo/Desbloqueo de cuentas
- ✅ Reset de contraseñas con generación automática de contraseñas temporales
- ✅ Filtros por estado (Activos, Inactivos, Bloqueados)
- ✅ Búsqueda en tiempo real por nombre o email
- ✅ Dashboard con estadísticas (Total, Activos, Inactivos, Bloqueados)
- ✅ Modal para mostrar contraseñas temporales con botón de copia
- ✅ Validaciones completas (email, password, unicidad)

**Archivos creados:**
- Backend: `backend/modules/usuarios.py` (700+ líneas)
- Frontend: `frontend/src/components/Usuarios.jsx` (800+ líneas)
- Estilos: `frontend/src/components/Usuarios.css` (600+ líneas)
- Documentación: [`MODULO_USUARIOS.md`](./MODULO_USUARIOS.md) ← **VER DOCUMENTACIÓN COMPLETA**

**Endpoints API:** `/api/usuarios/*` (11 endpoints REST)

---

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#-requisitos-previos)
2. [Inicio Rápido](#-inicio-rápido)
3. [Arquitectura del Sistema](#-arquitectura-del-sistema)
4. [Configuración Inicial](#-configuración-inicial)
5. [Autenticación y Seguridad](#-autenticación-y-seguridad)
6. [Solución de Problemas](#-solución-de-problemas)
7. [Desarrollo](#-desarrollo)

---

## 📋 Requisitos Previos

### Software Necesario
- **Python 3.13+** 
- **Node.js 18+** y **npm**
- **Git** (opcional)
- **Redis** (opcional, para caché)

### Conocimientos Recomendados
- Python (Flask, SQLAlchemy)
- JavaScript/React
- REST APIs
- JWT Authentication
- Supabase/PostgreSQL

---

## ⚡ Inicio Rápido

### **🎯 FORMA RECOMENDADA - Usar el comando `run.py`**

El sistema incluye un **script automatizado** que inicia ambos servidores simultáneamente:

```bash
# Desde CUALQUIER ubicación, simplemente ejecuta:
run.py
```

**¿Cómo funciona?**
1. ✅ Verifica que todas las dependencias estén instaladas
2. ✅ Inicia el **Backend (Flask)** en el puerto **5001**
3. ✅ Inicia el **Frontend (Vite)** en el puerto **5173**
4. ✅ Muestra las URLs de acceso
5. ✅ Monitorea ambos procesos
6. ✅ Al presionar `Ctrl+C`, detiene ambos servidores limpiamente

### **Métodos Alternativos**

#### Opción 1: Ejecutar desde el directorio principal
```bash
cd /Users/carlosalegria/Desktop/Migracion_OP
python run.py
```

#### Opción 2: Ejecutar desde el subdirectorio del proyecto
```bash
cd /Users/carlosalegria/Desktop/Migracion_OP/nuevo_proyecto
python run.py
```

#### Opción 3: Ruta absoluta (desde cualquier lugar)
```bash
python /Users/carlosalegria/Desktop/Migracion_OP/nuevo_proyecto/run.py
```

#### Opción 4: Script bash
```bash
cd /Users/carlosalegria/Desktop/Migracion_OP
./start.sh
```

---

## 🌐 URLs del Sistema

Una vez iniciado, el sistema está disponible en:

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Frontend** | http://localhost:5173 | Interfaz de usuario (React + Vite) |
| **Backend API** | http://localhost:5001 | API REST (Flask) |
| **Health Check** | http://localhost:5001/api/health | Verificación del estado del backend |
| **Login Endpoint** | http://localhost:5001/auth/login | Endpoint de autenticación |

---

## 🛑 Detener los Servidores

Para detener el sistema completo:

1. **Presiona `Ctrl + C`** en la terminal donde ejecutaste `run.py`
2. El script detendrá automáticamente:
   - ✅ Backend (Flask)
   - ✅ Frontend (Vite)
   - ✅ Todos los procesos relacionados

### Liberar Puertos Manualmente (si es necesario)

Si los puertos quedan ocupados:

```bash
# Liberar puerto 5001 (Backend)
lsof -ti:5001 | xargs kill -9

# Liberar puerto 5173 (Frontend)
lsof -ti:5173 | xargs kill -9

# Liberar ambos puertos
lsof -ti:5001,5173 | xargs kill -9
```

---

## 🏗️ Arquitectura del Sistema

### Stack Tecnológico

**Backend:**
- **Flask 3.0.3** - Framework web minimalista de Python
- **Supabase 2.5.1** - Base de datos PostgreSQL en la nube + Auth
- **Werkzeug 3.0.3** - Utilidades WSGI (hashing de contraseñas con scrypt)
- **PyJWT 2.8.0** - Generación y validación de tokens JWT
- **Redis 5.0.4** - Cache en memoria (opcional)
- **Python-dotenv 1.0.1** - Gestión de variables de entorno

**Frontend:**
- **React 19.1.1** - Librería para interfaces de usuario
- **Vite 7.1.7** - Build tool y dev server con HMR
- **ESLint 9.36.0** - Linter de código JavaScript

**Infraestructura:**
- **Gunicorn 22.0.0** - Servidor WSGI para producción
- **Gevent 24.11.1** - Worker asíncrono (compatible Python 3.13)

### Flujo de Autenticación

```
┌─────────────┐      1. POST /auth/login       ┌─────────────┐
│             │ ───────────────────────────────>│             │
│  Frontend   │      { email, password }        │   Backend   │
│  (React)    │                                 │   (Flask)   │
│             │<───────────────────────────────│             │
└─────────────┘   2. { token, user data }      └─────────────┘
                                                      │
                                                      │ 3. Consulta
                                                      │    usuario
                                                      ▼
                                               ┌─────────────┐
                                               │  Supabase   │
                                               │ (PostgreSQL)│
                                               └─────────────┘
```

**Proceso:**
1. Frontend envía credenciales vía proxy de Vite
2. Backend valida con Supabase
3. Verifica password con Werkzeug (scrypt)
4. Genera token JWT válido por 24h
5. Frontend almacena token en localStorage

---

## 📁 Estructura del Proyecto

```
Migracion_OP/
├── run.py                          # 🎯 Script wrapper principal (úsalo aquí)
├── start.sh                        # Script bash alternativo
├── setup_alias.sh                  # Configura alias en zsh
├── fix_alias.sh                    # Corrige alias antiguo
├── README.md                       # 📖 Esta documentación
├── CORRECCIONES.md                 # 📝 Registro de correcciones
├── .venv/                          # Entorno virtual de Python
│   └── bin/python                  # Python 3.13
│
└── nuevo_proyecto/
    ├── run.py                      # 🚀 Script de inicio principal
    ├── run_backend.py              # Lanzador del backend Flask
    ├── diagnose.py                 # 🔍 Script de diagnóstico
    ├── test_login.py               # 🧪 Script de prueba de login
    ├── .env                        # 🔐 Variables de entorno (NO SUBIR A GIT)
    │
    ├── backend/                    # 🐍 Backend Flask
    │   ├── __init__.py
    │   ├── app.py                  # Aplicación principal Flask
    │   ├── requirements.txt        # Dependencias Python
    │   │
    │   ├── models/                 # Modelos de datos
    │   │   ├── __init__.py
    │   │   └── user.py             # Modelo de Usuario
    │   │
    │   ├── modules/                # Módulos de la API
    │   │   ├── __init__.py
    │   │   └── auth.py             # 🔑 Autenticación (login)
    │   │
    │   └── utils/                  # Utilidades
    │       ├── __init__.py
    │       ├── cache.py            # Gestión de caché Redis
    │       └── decorators.py       # Decoradores personalizados
    │
    └── frontend/                   # ⚛️ Frontend React + Vite
        ├── package.json            # Dependencias Node.js
        ├── vite.config.js          # ⚙️ Configuración Vite + Proxy
        ├── eslint.config.js        # Configuración ESLint
        ├── index.html              # HTML base
        ├── public/                 # Archivos estáticos
        │
        └── src/
            ├── main.jsx            # Punto de entrada
            ├── App.jsx             # Componente raíz
            ├── App.css
            ├── index.css
            │
            ├── assets/             # Imágenes, fuentes, etc.
            │
            └── components/
                ├── Login.jsx       # 🔐 Componente de login
                └── Login.css
```

---

---

## ⚙️ Configuración Inicial

### 1. Variables de Entorno (`.env`)

El archivo `.env` en `nuevo_proyecto/.env` contiene las configuraciones críticas:

```env
# ============================================
# CONFIGURACIÓN DE SUPABASE
# ============================================
SUPABASE_URL=https://reubvhoexrkagmtxklek.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SECRET_KEY=tu_clave_secreta_para_jwt

# ============================================
# CONFIGURACIÓN DE GMAIL (opcional)
# ============================================
GMAIL_USER=opsomyl@gmail.com
GMAIL_PASS=nwak xdzx vdor uizh

# ============================================
# CONFIGURACIÓN DE REDIS (opcional)
# ============================================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0

# ============================================
# CONFIGURACIÓN DE FLASK
# ============================================
FLASK_ENV=development
FLASK_DEBUG=True
```

⚠️ **IMPORTANTE:** El archivo `.env` contiene información sensible. **NUNCA** lo subas a Git.

### 2. Base de Datos (Supabase)

La tabla `usuarios` debe tener la siguiente estructura:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `int8` | ID único (PRIMARY KEY) |
| `nombre` | `text` | Nombre completo del usuario |
| `email` | `text` | Correo electrónico (UNIQUE) |
| `password` | `text` | Contraseña hasheada con scrypt |
| `modulos` | `json` | Permisos/módulos del usuario |
| `creado_en` | `timestamp` | Fecha de creación |

**⚠️ Formato de Contraseña:**
```
scrypt:32768:8:1$salt$hash
```

Las contraseñas deben estar hasheadas con **Werkzeug's scrypt** (NO bcrypt).

### 3. Configuración del Proxy (Vite)

El archivo `frontend/vite.config.js` contiene la configuración del proxy:

```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
      },
      '/auth': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
```

**¿Qué hace el proxy?**
- Redirige peticiones de `/api/*` y `/auth/*` desde el frontend (5173) al backend (5001)
- Evita problemas de CORS
- Permite desarrollo local sin configuración adicional

---

## 🔐 Autenticación y Seguridad

### Sistema de Login

**Endpoint:** `POST /auth/login`

**Request:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "contraseña"
}
```

**Response (éxito):**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "nombre": "CARLOS ALEGRIA",
    "correo": "carlosalegria@me.com",
    "modulos": ["ordenes", "usuarios"]
  }
}
```

**Response (error):**
```json
{
  "message": "Usuario no encontrado"
}
```

### Algoritmo de Hashing

**⚠️ CRÍTICO:** Este sistema usa **Werkzeug's scrypt**, NO bcrypt.

```python
from werkzeug.security import check_password_hash

# Verificar contraseña
def check_password(self, password):
    return check_password_hash(self.hashed_password, password)
```

**¿Por qué scrypt?**
- Las contraseñas en la BD están en formato `scrypt:32768:8:1$...`
- Werkzeug viene incluido con Flask
- Es seguro y compatible con el sistema existente

### Tokens JWT

- **Algoritmo:** HS256
- **Expiración:** 24 horas
- **Contenido:**
  ```json
  {
    "user_id": 1,
    "nombre": "CARLOS ALEGRIA",
    "exp": 1729468800
  }
  ```
- **Almacenamiento:** localStorage del navegador

---

---

## 🐛 Solución de Problemas

### ❌ Problema 1: Error 404 en `/api/auth/login`

**Síntoma:**
```
Failed to load resource: :5173/api/auth/login:1 (404 NOT FOUND)
```

**Causa:** El proxy de Vite no estaba configurado correctamente.

**Solución:**
1. Configurar proxy en `vite.config.js`
2. **Reiniciar Vite** (Ctrl+C y volver a ejecutar `run.py`)
3. Recargar navegador con `Cmd + Shift + R` (forzar recarga sin caché)

---

### ❌ Problema 2: "Invalid salt" al hacer login

**Síntoma:**
```
Response status: 500
Response data: "Invalid salt"
```

**Causa:** El código usaba `bcrypt` pero las contraseñas están hasheadas con `scrypt`.

**Solución:**
```python
# ❌ ANTES (incorrecto)
import bcrypt
return bcrypt.checkpw(password.encode('utf-8'), self.hashed_password.encode('utf-8'))

# ✅ DESPUÉS (correcto)
from werkzeug.security import check_password_hash
return check_password_hash(self.hashed_password, password)
```

---

### ❌ Problema 3: Puerto 5001 o 5173 ocupado

**Síntoma:**
```
Address already in use
Port 5001 is in use by another program
```

**Solución:**
```bash
# Liberar puerto específico
lsof -ti:5001 | xargs kill -9

# Liberar ambos puertos
lsof -ti:5001,5173 | xargs kill -9
```

---

### ❌ Problema 4: Frontend envía 'correo' pero Backend espera 'email'

**Síntoma:**
```json
{ "message": "Faltan credenciales" }
```

**Solución:** Backend ahora acepta ambos campos:
```python
# Aceptar tanto 'email' como 'correo'
email = data.get('email') or data.get('correo')
```

---

### ❌ Problema 5: Dependencias incompatibles con Python 3.13

**Síntoma:**
```
gevent==24.2.1 no es compatible con Python 3.13
psycopg2-binary==2.9.9 falla al compilar
```

**Solución:**
- ✅ `gevent==24.2.1` → `gevent==24.11.1`
- ✅ `psycopg2-binary==2.9.9` → Eliminado (no necesario con Supabase)
- ✅ Agregado `bcrypt==4.2.1`

---

### ❌ Problema 6: Error "Unexpected token '<', '<!doctype'..."

**Síntoma:** El servidor devuelve HTML en lugar de JSON.

**Causa:** El proxy no redirige correctamente o la ruta es incorrecta.

**Solución:**
1. Verificar que la ruta sea `/auth/login` (no `/api/auth/login`)
2. Reiniciar Vite para que cargue la nueva configuración
3. Limpiar caché del navegador

---

### 🔍 Herramientas de Diagnóstico

#### Script de Diagnóstico del Backend
```bash
cd nuevo_proyecto
python diagnose.py
```

**Verifica:**
- ✅ Imports correctos
- ✅ Variables de entorno (.env)
- ✅ Conexión a Supabase
- ✅ Rutas registradas en Flask

#### Probar Login Manualmente
```bash
cd nuevo_proyecto
python test_login.py
```

#### Verificar Health Check
```bash
curl http://localhost:5001/api/health
```

**Respuesta esperada:**
```json
{
  "status": "ok",
  "message": "API funcionando!"
}
```

#### Probar Login con cURL
```bash
curl -X POST http://localhost:5001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"carlosalegria@me.com","password":"camilo"}'
```

---

### 📝 Checklist de Problemas Comunes

- [ ] ¿Los puertos 5001 y 5173 están libres?
- [ ] ¿El archivo `.env` existe y tiene las variables correctas?
- [ ] ¿El entorno virtual está activado?
- [ ] ¿Las dependencias de Python están instaladas?
- [ ] ¿Las dependencias de npm están instaladas?
- [ ] ¿Recargaste el navegador después de cambios en Vite?
- [ ] ¿El proxy está configurado en `vite.config.js`?
- [ ] ¿Las contraseñas están hasheadas con scrypt (no bcrypt)?

---

---

## � Desarrollo

### Entorno de Desarrollo

**Hot Module Replacement (HMR):**
- Frontend: Los cambios se reflejan **instantáneamente** sin recargar
- Backend: Flask reinicia automáticamente en modo debug

### Flujo de Trabajo Recomendado

1. **Iniciar el sistema:**
   ```bash
   run.py
   ```

2. **Abrir tu editor de código** (VSCode, PyCharm, etc.)

3. **Realizar cambios:**
   - Frontend: Los cambios se ven inmediatamente
   - Backend: El servidor se reinicia automáticamente

4. **Probar en el navegador:**
   - Frontend: http://localhost:5173
   - API: http://localhost:5001

5. **Consultar logs:**
   - Los logs de ambos servidores se muestran en la terminal

### Estructura de Archivos Importantes

**Backend:**
- `backend/app.py` - Configuración principal de Flask
- `backend/modules/auth.py` - Lógica de autenticación
- `backend/models/user.py` - Modelo de usuario
- `backend/requirements.txt` - Dependencias Python

**Frontend:**
- `frontend/src/App.jsx` - Componente raíz
- `frontend/src/components/Login.jsx` - Componente de login
- `frontend/vite.config.js` - Configuración de Vite + Proxy
- `frontend/package.json` - Dependencias npm

### Agregar Nuevas Rutas

**Backend (Flask):**
```python
# En backend/modules/ordenes.py
from flask import Blueprint, jsonify

bp = Blueprint("ordenes", __name__)

@bp.route("/list", methods=["GET"])
def list_ordenes():
    return jsonify({"ordenes": []})
```

```python
# Registrar en backend/app.py
from .modules.ordenes import bp as ordenes_bp
app.register_blueprint(ordenes_bp, url_prefix='/api/ordenes')
```

**Frontend (React):**
```javascript
// Agregar proxy en vite.config.js si es necesario
proxy: {
  '/api': {
    target: 'http://localhost:5001',
    changeOrigin: true,
  }
}
```

---

## � Instalación Manual

Si necesitas instalar las dependencias por separado:

### Backend (Python)
```bash
cd nuevo_proyecto/backend
pip install -r requirements.txt
```

**Dependencias clave:**
- Flask 3.0.3
- Supabase 2.5.1
- Werkzeug 3.0.3
- PyJWT 2.8.0
- Redis 5.0.4
- Gevent 24.11.1 (compatible Python 3.13)

### Frontend (Node.js)
```bash
cd nuevo_proyecto/frontend
npm install
```

**Dependencias clave:**
- React 19.1.1
- Vite 7.1.7
- ESLint 9.36.0

---

## � Comandos Útiles

### Gestión del Sistema

```bash
# Iniciar todo el sistema
run.py

# Verificar puertos ocupados
lsof -ti:5001,5173

# Liberar puertos
lsof -ti:5001,5173 | xargs kill -9

# Ver logs del backend
tail -f logs/backend.log

# Verificar estado del backend
curl http://localhost:5001/api/health
```

### Desarrollo

```bash
# Activar entorno virtual
source .venv/bin/activate

# Instalar nueva dependencia Python
pip install nombre_paquete
pip freeze > backend/requirements.txt

# Instalar nueva dependencia npm
cd frontend
npm install nombre_paquete

# Ejecutar tests
pytest backend/tests/

# Linter Python
flake8 backend/

# Linter JavaScript
cd frontend && npm run lint
```

### Base de Datos

```bash
# Conectar a Supabase (psql)
psql postgresql://[YOUR_CONNECTION_STRING]

# Ver usuarios
SELECT id, nombre, email FROM usuarios;

# Hashear contraseña nueva (Python)
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('nueva_password'))"
```

### Debugging

```bash
# Ver requests en tiempo real (Backend)
tail -f logs/access.log

# Probar endpoint con curl
curl -X POST http://localhost:5001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}' \
  -v

# Ver variables de entorno
cat nuevo_proyecto/.env

# Diagnosticar backend
cd nuevo_proyecto && python diagnose.py

# Probar login automáticamente
cd nuevo_proyecto && python test_login.py
```

---

## � Recursos Adicionales

### Documentación Oficial
- [Flask](https://flask.palletsprojects.com/)
- [React](https://react.dev/)
- [Vite](https://vitejs.dev/)
- [Supabase](https://supabase.com/docs)
- [Werkzeug Security](https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security)

### Archivos de Referencia
- `CORRECCIONES.md` - Historial de correcciones realizadas
- `diagnose.py` - Script de diagnóstico del sistema
- `test_login.py` - Script de prueba de autenticación

---

## 🔐 Seguridad

### Buenas Prácticas Implementadas

✅ **Contraseñas hasheadas** con scrypt (Werkzeug)  
✅ **Tokens JWT** con expiración de 24h  
✅ **Variables de entorno** para credenciales  
✅ **HTTPS** en producción (Supabase)  
✅ **Validación de inputs** en backend  
✅ **CORS** manejado por proxy de Vite  

### Recomendaciones

⚠️ **NUNCA** subir `.env` a Git  
⚠️ **CAMBIAR** `SECRET_KEY` en producción  
⚠️ **USAR** HTTPS en producción  
⚠️ **ROTAR** tokens regularmente  
⚠️ **VALIDAR** siempre en backend (nunca confiar solo en frontend)  

---

## 📞 Soporte

### Problemas Comunes

1. **Login no funciona** → Ver sección "Solución de Problemas"
2. **Puerto ocupado** → `lsof -ti:5001,5173 | xargs kill -9`
3. **Dependencias** → Reinstalar con `pip install -r requirements.txt`

### Contacto

Para dudas técnicas o soporte:
- Email: opsomyl@gmail.com
- Revisar: `CORRECCIONES.md` para problemas ya resueltos

---

## 📄 Licencia

Proyecto privado - Todos los derechos reservados

---

## 🧭 Cambios recientes: Sidebar (menú lateral)

Se ha mejorado y estandarizado el componente del sidebar en el frontend para acercarlo al diseño proporcionado y mejorar la usabilidad.

Archivos modificados
- `nuevo_proyecto/frontend/src/components/Sidebar.jsx` — Lógica del componente: colapsado, submenús exclusivos, footer con botón de logout.
- `nuevo_proyecto/frontend/src/components/Sidebar.css` — Estilos: versión colapsada, overlay de submenús, estilos del footer, ajustes de tamaños.
- `nuevo_proyecto/frontend/src/App.jsx` — Se pasó la función `handleLogout` al `Sidebar` para que el botón de cierre de sesión esté dentro del menú lateral.

Características implementadas
- Botón para contraer/expandir el sidebar (estado `isCollapsed`).
- Solo un submenú abierto a la vez (al abrir otro, el anterior se cierra).
- Cuando el sidebar está colapsado, los submenús se muestran como un overlay flotante.
- Botón "Cerrar Sesión" movido al footer del sidebar y estilizado; en modo colapsado muestra sólo el icono.
- Iconos alineados a la izquierda; el item "Administración del Sistema" usa un único icono.
- Ajustes de tipografía y padding para que los labels quepan correctamente.

Cómo probar localmente
1. Arranca el sistema (desde la raíz del proyecto):

```bash
python run.py
```

2. Abre el frontend (normalmente en `http://localhost:5173`).
3. Inicia sesión si la app lo requiere.
4. Interactúa con el sidebar:
  - Haz clic en el botón naranja superior para contraer/expandir.
  - Abre un submenú y luego otro: el anterior debe cerrarse automáticamente.
  - Con el sidebar colapsado, abre un submenú para ver el overlay flotante.
  - El botón "Cerrar Sesión" está al final del panel lateral.

Notas y próximas mejoras sugeridas
- Cerrar el overlay al hacer clic fuera (mejora de UX).
- Usar SVGs o una librería de iconos (por ejemplo `react-icons`) en lugar de emojis para consistencia visual.
- Persistir el estado `isCollapsed` en `localStorage` si se desea que la preferencia se mantenga entre recargas.

Si quieres que implemente alguna de estas mejoras, dime cuál y la agrego.

## 🎯 Próximos Pasos

- [ ] Implementar refresh tokens
- [ ] Agregar logout
- [ ] Protección de rutas en React
- [ ] Middleware de autenticación en Flask
- [ ] Tests unitarios
- [ ] Tests de integración
- [ ] Documentación API (Swagger)
- [ ] CI/CD pipeline
- [ ] Despliegue en producción

---

**Última actualización:** 3 de noviembre de 2025  
**Versión:** 1.0.1  
**Estado:** ✅ Producción

---

## 📝 Registro de Trabajo Reciente

### 🔧 3 de Noviembre de 2025: Fix Módulo `ordenes_no_recepcionadas`

**PROBLEMA CRÍTICO RESUELTO:** El módulo mostraba 376 órdenes pendientes cuando en producción solo hay 31.

#### 🔍 Diagnóstico

**Causa raíz identificada:**
1. ❌ **Falta de paginación** - Solo se obtenían los primeros 1000 registros de Supabase
2. ❌ **Falta filtro de fecha** - Se mostraban OCs de más de 2 años de antigüedad

**Proceso de diagnóstico:**
- Comparación con sistema en producción (https://pagos.datix.cl)
- Análisis de código antiguo en repositorio `CarlosATO/seguimiento_ordenes`
- Scripts de diagnóstico creados:
  - `diagnostico_oc_pendientes.py` - Análisis inicial
  - `diagnostico_filtros_avanzado.py` - Análisis de filtros por fecha/monto
  - `test_fecha_exacta.py` - Identificación del período exacto

#### ✅ Soluciones Implementadas

**Archivo modificado:** `nuevo_proyecto/backend/modules/ordenes_no_recepcionadas.py`

**Cambios aplicados:**

1. **Paginación completa para ingresos:**
```python
def get_all_ingresos(supabase):
    """Obtiene TODOS los ingresos con paginación"""
    all_ingresos = []
    start = 0
    page_size = 1000
    
    while True:
        response = supabase.table("ingresos").select(
            "orden_compra, art_corr"
        ).range(start, start + page_size - 1).execute()
        
        rows = response.data or []
        if not rows or len(rows) < page_size:
            break
        
        all_ingresos.extend(rows)
        start += page_size
    
    return all_ingresos
```

2. **Paginación completa para órdenes de compra:**
```python
# Obtener TODAS las líneas con paginación
oc_lines = []
start = 0
page_size = 1000

while True:
    response = supabase.table("orden_de_compra").select(
        "orden_compra, proveedor, fecha, total, art_corr, elimina_oc"
    ).gte("fecha", fecha_limite).order("orden_compra", desc=True).range(
        start, start + page_size - 1
    ).execute()
    
    rows = response.data or []
    if not rows or len(rows) < page_size:
        break
    
    oc_lines.extend(rows)
    start += page_size
```

3. **Filtro de fecha (último año):**
```python
from datetime import datetime, timedelta

# Calcular fecha límite (último año - 12 meses)
fecha_limite = (datetime.now() - timedelta(days=365)).date().isoformat()

# Aplicar filtro en la consulta
.gte("fecha", fecha_limite)
```

#### 📊 Resultados

**Antes del fix:**
- Total OCs mostradas: **376**
- Monto total: $407,113,917
- Causa: Solo primeros 1000 registros + sin filtro de fecha

**Después del fix:**
- Total OCs mostradas: **31** ✅
- Monto total: **$19,331,932** ✅
- 100% coincidente con sistema en producción

#### 🎯 Lógica del Sistema

El módulo aplica la siguiente lógica (idéntica al sistema antiguo):

1. Obtiene **TODAS** las líneas de órdenes de compra (con paginación)
2. Obtiene **TODOS** los ingresos registrados (con paginación)
3. Filtra solo OCs del **último año**
4. Filtra OCs no marcadas como eliminadas (`elimina_oc != "1"`)
5. Compara línea por línea usando tupla `(orden_compra, art_corr)`
6. Una OC se considera pendiente si tiene **AL MENOS UNA** línea sin ingreso
7. El monto mostrado es la **suma SOLO de las líneas pendientes**

#### ⚠️ Lecciones Aprendidas

**IMPORTANTE para futuros desarrollos:**

1. **SIEMPRE usar paginación** con Supabase (límite por defecto ~1000 registros)
2. **Verificar filtros de fecha** - sistemas en producción suelen mostrar solo datos recientes
3. **Comparar resultados** con sistema antiguo antes de implementar
4. **Usar scripts de diagnóstico** para validar lógica de negocio

#### 🔗 Referencias

- Sistema en producción: https://pagos.datix.cl
- Código antiguo: https://github.com/CarlosATO/seguimiento_ordenes/blob/main/app/modules/informes.py
- Tablas involucradas:
  - `orden_de_compra` - Líneas de órdenes de compra
  - `ingresos` - Recepciones de materiales/servicios
  - `proveedores` - Información de proveedores

---

### 📌 Módulo `pagos` (20 de Octubre de 2025)

Pequeño resumen técnico de las acciones realizadas durante la migración y diagnóstico (útil para quien retome el trabajo):

- Archivo editado: `nuevo_proyecto/backend/modules/pagos.py`
  - Alineé `get_stats` con la lógica de `list_pagos` (batch-fetch y agregación por `orden_numero`).
  - Pasé las sumas monetarias a enteros redondeados con `int(round(...))` para evitar errores por precisión de punto flotante.
  - Cambié la lógica de `calcular_estado_pago` para priorizar `abono` en abonos parciales (si hay abonos y queda saldo > 0 → `abono`; si saldo == 0 o hay fecha → `pagado`).
  - Añadido endpoint de diagnóstico: `/api/pagos/stats?debug=1` (devuelve muestras y contadores para inspección rápida).
  - Añadido mapeo básico para parámetros `estado` recibidos desde la UI (ej. `Con Abonos` → `abono`) para mejorar compatibilidad mientras se ajusta el frontend.

Resultados observados en pruebas locales:

- Orden 3188: ahora aparece como `pagado` con `saldo_pendiente: 0` (abonos suman exactamente el total).
- Órdenes 3144 y 3126: aparecen como `abono` con `total_abonado` y `saldo_pendiente` correctos.
- `/api/pagos/stats?debug=1` devuelve métricas coherentes con la vista detallada.

Pendiente: todavía existe un desfase al filtrar desde la UI en algunos casos (la UI envía etiquetas human-readable y puede haber diferencias en el mapeo, ver `TAREAS_PENDIENTES.md`).

Si retomas trabajo en `pagos`, revisa primero `TAREAS_PENDIENTES.md` y el ticket/branch: `backup-before-proveedores-change-20251024-130912`.
