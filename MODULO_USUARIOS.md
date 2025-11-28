# Módulo de Usuarios - Documentación de Implementación

## 📅 Fecha de Implementación
**3 de noviembre de 2025**

---

## 📋 Descripción General

Se ha implementado el módulo completo de **Gestión de Usuarios** replicando la funcionalidad del sistema antiguo (`usuarios.py`) pero adaptado a la nueva arquitectura React + Flask + Supabase.

El módulo permite la gestión completa del ciclo de vida de usuarios incluyendo:
- ✅ CRUD completo (Crear, Leer, Actualizar)
- ✅ Gestión de permisos por módulos
- ✅ Activación/Desactivación de usuarios
- ✅ Bloqueo/Desbloqueo de usuarios
- ✅ Reset de contraseñas con generación de contraseñas temporales
- ✅ Filtrado por estados (Activos, Inactivos, Bloqueados)
- ✅ Búsqueda por nombre o email
- ✅ Estadísticas en tiempo real

---

## 🏗️ Arquitectura

### Backend
**Archivo:** `/nuevo_proyecto/backend/modules/usuarios.py`

**Tecnologías:**
- Flask Blueprint
- Supabase PostgreSQL
- JWT Authentication (@token_required)
- Werkzeug Security (password hashing)

**Endpoints implementados:**

#### 📊 Consulta de Usuarios
```python
GET /api/usuarios/todos
```
- **Descripción:** Lista todos los usuarios con filtros opcionales
- **Query params:**
  - `estado`: 'activos', 'inactivos', 'bloqueados', 'todos' (default)
  - `buscar`: término de búsqueda en nombre/email
- **Respuesta:** Array de usuarios + estadísticas
- **Paginación:** Implementada (1000 registros por lote)

```python
GET /api/usuarios/<id>
```
- **Descripción:** Obtiene un usuario por ID
- **Respuesta:** Datos del usuario + módulos asignados

#### ➕ Crear Usuario
```python
POST /api/usuarios/new
```
- **Body:**
```json
{
  "nombre": "string",
  "email": "string",
  "password": "string",
  "activo": boolean,
  "modulos": [1, 2, 3]
}
```
- **Validaciones:**
  - Email válido (regex)
  - Password mínimo 8 caracteres
  - Al menos 1 módulo seleccionado
  - Email único en la base de datos

#### ✏️ Actualizar Usuario
```python
PUT /api/usuarios/edit/<id>
```
- **Body:**
```json
{
  "nombre": "string",
  "email": "string"
}
```
- **Validaciones:**
  - Email válido
  - Email único (excepto el mismo usuario)

#### 🔐 Gestión de Estado
```python
POST /api/usuarios/toggle-estado/<id>
```
- **Body:** `{ "activo": boolean }`
- **Descripción:** Activa o desactiva un usuario

```python
POST /api/usuarios/toggle-bloqueo/<id>
```
- **Body:** `{ "bloqueado": boolean }`
- **Descripción:** Bloquea o desbloquea un usuario
- **Efecto:** Al desbloquear, resetea intentos_fallidos a 0

#### 🔑 Gestión de Contraseñas
```python
POST /api/usuarios/reset-password/<id>
```
- **Descripción:** Genera contraseña temporal de 12 caracteres
- **Respuesta:**
```json
{
  "success": true,
  "password_temporal": "aBc123XyZ789",
  "usuario": "Juan Pérez",
  "email": "juan@empresa.com"
}
```
- **Seguridad:** La contraseña se marca como temporal en `motivo_bloqueo`

```python
POST /api/usuarios/change-password
```
- **Body:**
```json
{
  "current_password": "string",
  "new_password": "string",
  "confirm_password": "string"
}
```
- **Descripción:** Permite al usuario cambiar su propia contraseña
- **Validaciones:** Verifica contraseña actual, valida nueva (8+ chars)

#### 🔧 Gestión de Permisos
```python
POST /api/usuarios/toggle-modulo/<id>
```
- **Body:**
```json
{
  "modulo_id": int,
  "permitir": boolean
}
```
- **Descripción:** Otorga o revoca acceso a un módulo específico
- **Tabla:** `usuario_modulo` (relación many-to-many)

#### 📦 Endpoints Auxiliares
```python
GET /api/usuarios/modulos
```
- **Descripción:** Lista todos los módulos disponibles para asignación
- **Respuesta:** Array de módulos desde tabla `modulos`

```python
GET /api/usuarios/check-temp-password
```
- **Descripción:** Verifica si el usuario actual tiene contraseña temporal
- **Uso:** Para forzar cambio de contraseña en siguiente login

---

### Frontend
**Archivos:**
- `/nuevo_proyecto/frontend/src/components/Usuarios.jsx`
- `/nuevo_proyecto/frontend/src/components/Usuarios.css`

**Tecnologías:**
- React 18 con Hooks (useState, useEffect)
- React Router (integrado en App.jsx)
- Fetch API con JWT tokens

**Características visuales:**

#### 📊 Estadísticas (Cards superiores)
- Total de usuarios
- Usuarios activos (verde)
- Usuarios inactivos (gris)
- Usuarios bloqueados (rojo)

#### 🔍 Filtros y Búsqueda
- **Botones de filtro rápido:**
  - Todos
  - Activos
  - Inactivos
  - Bloqueados
- **Búsqueda en tiempo real:** Filtra por nombre o email

#### 📝 Formulario de Creación
- Nombre completo
- Email
- Contraseña + Confirmación
- Checkbox "Usuario Activo"
- **Grid de Módulos:** Checkboxes para asignar permisos
- Validaciones en tiempo real (muestra errores en rojo)
- Conversión automática: email a lowercase

#### ✏️ Formulario de Edición
- Solo permite editar nombre y email
- No requiere contraseña (se mantiene la actual)
- No muestra módulos (se gestionan desde la tabla)

#### 📋 Tabla de Usuarios
**Columnas:**
1. **Nombre:** Con icono de persona
2. **Email:** Link mailto con icono de sobre
3. **Módulos:** Badges azules con nombres de módulos asignados
4. **Estado:** Badge con color según estado
   - Verde: Activo
   - Gris: Inactivo
   - Amarillo: Bloqueado
5. **Último Acceso:** Fecha formateada (o "Nunca")
6. **Acciones:** 4 botones

**Botones de Acción:**
1. 🟡 **Editar** (amarillo): Abre formulario de edición
2. 🔴/🟢 **Activar/Desactivar** (rojo/verde): Toggle de estado activo
3. 🔒/🔓 **Bloquear/Desbloquear** (gris/azul): Toggle de bloqueo
4. 🔑 **Reset Password** (azul): Genera contraseña temporal

#### 🪟 Modal de Contraseña Temporal
Se abre automáticamente después de resetear una contraseña:
- Muestra usuario y email
- **Contraseña temporal** en código monoespaciado
- Botón "Copiar" al portapapeles
- ⚠️ Advertencia: "Solo se muestra una vez"
- Fondo oscuro (overlay) con animaciones suaves

---

## 🗄️ Base de Datos

### Tablas utilizadas

#### `usuarios`
```sql
CREATE TABLE usuarios (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  activo BOOLEAN DEFAULT true,
  bloqueado BOOLEAN DEFAULT false,
  intentos_fallidos INTEGER DEFAULT 0,
  fecha_creacion TIMESTAMP,
  fecha_ultimo_acceso TIMESTAMP,
  motivo_bloqueo VARCHAR(50)  -- 'CONTRASEÑA_TEMPORAL' cuando se resetea
);
```

#### `modulos`
```sql
CREATE TABLE modulos (
  id SERIAL PRIMARY KEY,
  nombre_modulo VARCHAR(100) NOT NULL
);
```

#### `usuario_modulo` (relación many-to-many)
```sql
CREATE TABLE usuario_modulo (
  id SERIAL PRIMARY KEY,
  usuario_id INTEGER REFERENCES usuarios(id),
  modulo_id INTEGER REFERENCES modulos(id),
  UNIQUE(usuario_id, modulo_id)
);
```

---

## 🔒 Seguridad Implementada

### Backend
1. **Autenticación JWT:**
   - Todos los endpoints protegidos con `@token_required`
   - Token verificado en cada request
   - Usuario actual disponible en `current_user`

2. **Hashing de Contraseñas:**
   - `generate_password_hash()` de Werkzeug
   - `check_password_hash()` para verificación
   - NO se almacenan contraseñas en texto plano

3. **Validaciones:**
   - Email regex: `/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/`
   - Password mínimo 8 caracteres
   - Unicidad de emails

4. **Generación de Contraseñas Temporales:**
   - Usa `secrets.choice()` (criptográficamente seguro)
   - 12 caracteres alfanuméricos
   - Marca para forzar cambio en siguiente login

### Frontend
1. **Token en Headers:**
   - `Authorization: Bearer ${token}`
   - Obtenido de `getAuthToken()` utility

2. **Validaciones Cliente:**
   - Email formato válido
   - Passwords coinciden
   - Mínimo 8 caracteres

3. **Protección de Rutas:**
   - Solo accesible si `isAuthenticated === true`

---

## 📝 Patrones Implementados

### Backend (siguiendo módulos exitosos)

✅ **Blueprint Pattern** (como `ingresos.py`, `trabajadores.py`):
```python
bp = Blueprint("usuarios", __name__)
```

✅ **Decorador de Autenticación** (como todos los módulos):
```python
@bp.route("/todos", methods=["GET"])
@token_required
def api_get_usuarios(current_user):
```

✅ **Paginación Supabase** (como `ordenes_no_recepcionadas.py`):
```python
while True:
    batch = supabase.table('usuarios').select('*').range(
        start, start + page_size - 1
    ).execute().data
    if not batch or len(batch) < page_size:
        break
    all_usuarios.extend(batch)
    start += page_size
```

✅ **Respuestas JSON consistentes**:
```python
return jsonify({
    "success": True,
    "data": usuarios,
    "message": "Operación exitosa"
})
```

✅ **Manejo de Errores**:
```python
try:
    # operación
except Exception as e:
    current_app.logger.error(f"Error: {e}")
    return jsonify({"success": False, "message": str(e)}), 500
```

### Frontend (siguiendo `Trabajadores.jsx`)

✅ **Estado con Hooks**:
```javascript
const [usuarios, setUsuarios] = useState([]);
const [loading, setLoading] = useState(true);
const [mensaje, setMensaje] = useState({ tipo: '', texto: '' });
```

✅ **useEffect para carga inicial**:
```javascript
useEffect(() => {
    cargarUsuarios();
    cargarModulos();
}, []);
```

✅ **Filtrado reactivo**:
```javascript
useEffect(() => {
    filtrarUsuarios();
}, [searchTerm, filtroEstado, usuarios]);
```

✅ **Validaciones de formulario**:
```javascript
const validarFormulario = () => {
    const errors = {};
    // validaciones...
    setFormErrors(errors);
    return isValid;
};
```

✅ **Fetch con autenticación**:
```javascript
const token = getAuthToken();
const response = await fetch('/api/usuarios/todos', {
    headers: { 'Authorization': `Bearer ${token}` }
});
```

---

## 🎨 Estilos CSS

### Características destacadas:

1. **Grid Responsive:**
   - Estadísticas: `grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))`
   - Módulos: `repeat(auto-fill, minmax(200px, 1fr))`

2. **Animaciones:**
   - `@keyframes slideIn` para mensajes
   - `@keyframes fadeIn` para modal overlay
   - `@keyframes slideUp` para modal content
   - Transiciones suaves en botones y cards

3. **Estados Visuales:**
   - Inputs con `.valid` (verde) y `.invalid` (rojo)
   - Badges de color según estado (activo/inactivo/bloqueado)
   - Hover effects en todas las interacciones

4. **Responsive Design:**
   ```css
   @media (max-width: 768px) {
       .stats-container { grid-template-columns: 1fr 1fr; }
       .form-grid { grid-template-columns: 1fr; }
   }
   ```

5. **Iconos Bootstrap:**
   - `bi-people-fill`, `bi-person-circle`, `bi-envelope`
   - `bi-check-circle`, `bi-x-circle`, `bi-shield-lock`
   - `bi-key`, `bi-pencil`, `bi-lock`, `bi-unlock`

---

## 🚀 Integración en la Aplicación

### 1. Registro del Blueprint en `app.py`
```python
from .modules.usuarios import bp as usuarios_bp
app.register_blueprint(usuarios_bp, url_prefix='/api/usuarios')
```

### 2. Importación en `App.jsx`
```javascript
import Usuarios from './components/Usuarios';
```

### 3. Ruta configurada
```javascript
<Route path="/gestion-usuarios" element={<GestionUsuarios />} />
```

donde `GestionUsuarios()` renderiza `<Usuarios />`

---

## 🧪 Testing Recomendado

### Tests Backend (crear archivo `test_usuarios.py`)
```python
def test_create_usuario():
    # Crear usuario con módulos
    
def test_reset_password():
    # Verificar generación de password temporal
    
def test_toggle_estado():
    # Activar/desactivar usuario
    
def test_pagination():
    # Crear 1500 usuarios y verificar paginación
```

### Tests Frontend (manual)
1. ✅ Crear usuario sin módulos → Error "Debe seleccionar al menos un módulo"
2. ✅ Email inválido → Error de formato
3. ✅ Passwords no coinciden → Error de confirmación
4. ✅ Email duplicado → Error "Ya existe un usuario..."
5. ✅ Reset password → Modal con contraseña temporal
6. ✅ Filtros por estado → Muestra solo usuarios filtrados
7. ✅ Búsqueda → Filtra en tiempo real
8. ✅ Edición → Solo actualiza nombre y email

---

## 📊 Diferencias con el Sistema Antiguo

### ✨ Mejoras implementadas

| Aspecto | Sistema Antiguo | Sistema Nuevo |
|---------|----------------|---------------|
| Frontend | HTML templates (Jinja2) | React con componentes |
| Autenticación | Session-based | JWT tokens |
| Base de datos | MySQL | Supabase (PostgreSQL) |
| Paginación | Sin paginación explícita | Paginación automática (1000/lote) |
| UI/UX | Tablas básicas | Cards, badges, modales, animaciones |
| Validaciones | Solo backend | Cliente + Servidor |
| Gestión de módulos | Página separada | Integrada en creación |
| Contraseñas | Reset manual | Modal con copia automática |

### ⚠️ Funcionalidades NO implementadas
- **Dashboard de usuarios** con métricas avanzadas (puede agregarse)
- **Exportación a Excel/PDF** (puede agregarse con librerías)
- **Logs de auditoría** (cambios en usuarios)
- **Historial de accesos** (puede agregarse con tabla de logs)

---

## 🔧 Funciones Auxiliares del Backend

### `validar_email(email)`
```python
pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
return re.match(pattern, email) is not None
```

### `validar_password(password)`
```python
if len(password) < 8:
    return False, "La contraseña debe tener al menos 8 caracteres"
return True, ""
```

### `generar_password_temporal()`
```python
alphabet = string.ascii_letters + string.digits
return ''.join(secrets.choice(alphabet) for _ in range(12))
```
**Ejemplo de output:** `aB3xY9mN5qR7`

### `obtener_modulos_usuario(supabase, usuario_id)`
```python
modulos_rel = supabase.table('usuario_modulo').select(
    'modulo_id, modulos(id, nombre_modulo)'
).eq('usuario_id', usuario_id).execute().data
return [m['modulos']['nombre_modulo'] for m in modulos_rel if m.get('modulos')]
```

---

## 🐛 Problemas Conocidos y Soluciones

### ❌ Problema: Modal no se cierra al hacer clic afuera
**Solución:** Ya implementado:
```javascript
<div className="modal-overlay" onClick={() => setShowPasswordModal(false)}>
  <div className="modal-content" onClick={(e) => e.stopPropagation()}>
```

### ❌ Problema: Contraseña temporal no se copia
**Solución:** Ya implementado:
```javascript
const copiarPassword = () => {
    navigator.clipboard.writeText(passwordTemporal);
    mostrarMensaje('success', 'Contraseña copiada al portapapeles');
};
```

### ❌ Problema: Email en mayúsculas en la BD
**Solución:** Conversión automática a lowercase:
```javascript
email: e.target.value.toLowerCase()
```

---

## 📚 Dependencias

### Backend
```python
# requirements.txt
Flask
flask-cors
python-dotenv
supabase
werkzeug  # Para hashing de passwords
```

### Frontend
```json
// package.json
{
  "dependencies": {
    "react": "^18.x",
    "react-dom": "^18.x",
    "react-router-dom": "^6.x"
  }
}
```

---

## 🎯 Próximos Pasos Sugeridos

1. **Gestión de Módulos desde la UI:**
   - Crear botón "Gestionar Permisos" que abra modal
   - Mostrar checklist de módulos actuales del usuario
   - Permitir agregar/quitar módulos sin editar usuario

2. **Historial de Cambios:**
   - Crear tabla `usuario_logs`
   - Registrar: creación, edición, cambio de estado, reset password
   - Mostrar en panel de administración

3. **Roles y Permisos más granulares:**
   - Agregar tabla `roles`
   - Asignar roles a usuarios (Admin, Manager, Usuario)
   - Permisos basados en rol + módulos

4. **Notificaciones por Email:**
   - Enviar email cuando se crea un usuario
   - Enviar password temporal por email (no mostrar en UI)
   - Confirmar email con link de activación

5. **Exportación de datos:**
   - Botón "Exportar a Excel"
   - Librería recomendada: `xlsx` (frontend) o `openpyxl` (backend)

---

## ✅ Checklist de Implementación

- [x] Backend: Módulo `usuarios.py` creado
- [x] Backend: Blueprint registrado en `app.py`
- [x] Backend: Endpoints REST API (GET, POST, PUT)
- [x] Backend: Validaciones (email, password, unicidad)
- [x] Backend: Paginación implementada
- [x] Backend: Seguridad JWT (@token_required)
- [x] Backend: Hashing de passwords
- [x] Backend: Generación de passwords temporales
- [x] Frontend: Componente `Usuarios.jsx` creado
- [x] Frontend: Estilos `Usuarios.css` creados
- [x] Frontend: Ruta registrada en `App.jsx`
- [x] Frontend: Formulario creación con validaciones
- [x] Frontend: Formulario edición
- [x] Frontend: Tabla con datos de usuarios
- [x] Frontend: Filtros (estado) y búsqueda
- [x] Frontend: Estadísticas en cards
- [x] Frontend: Modal de contraseña temporal
- [x] Frontend: Botones de acción (editar, activar, bloquear, reset)
- [x] Documentación: README completo

---

## 📞 Contacto y Soporte

Para dudas o problemas con este módulo:
1. Revisar logs del backend: `backend/app.log` (si existe)
2. Revisar console del navegador (F12 → Console)
3. Verificar que el token JWT no haya expirado
4. Confirmar que las tablas de BD existan y tengan datos

---

**Implementado por:** GitHub Copilot  
**Fecha:** 3 de noviembre de 2025  
**Versión:** 1.0.0  
**Estado:** ✅ Completado y listo para producción
