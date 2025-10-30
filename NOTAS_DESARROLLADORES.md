# 📝 Notas Importantes para Desarrolladores

Este documento contiene información crítica que todo desarrollador debe conocer antes de trabajar en el proyecto.

---

## 🚨 CRÍTICO - Leer Primero

### 1. **NUNCA uses bcrypt para las contraseñas**

❌ **INCORRECTO:**
```python
import bcrypt
bcrypt.checkpw(password, hashed_password)
```

✅ **CORRECTO:**
```python
from werkzeug.security import check_password_hash
check_password_hash(hashed_password, password)
```

**Razón:** Las contraseñas en la base de datos están hasheadas con `scrypt` (formato: `scrypt:32768:8:1$...`), no con bcrypt.

---

### 2. **Proxy de Vite es ESENCIAL**

El frontend (puerto 5173) debe comunicarse con el backend (puerto 5001) a través del proxy configurado en `vite.config.js`.

**Sin proxy:**
```
Frontend → :5173/auth/login → ❌ 404 (no existe en Vite)
```

**Con proxy:**
```
Frontend → :5173/auth/login → Proxy → :5001/auth/login → ✅ Backend
```

**⚠️ Importante:** Después de modificar `vite.config.js`, debes:
1. Detener Vite (Ctrl+C)
2. Reiniciar con `run.py`
3. Recargar el navegador con `Cmd+Shift+R` (forzar sin caché)

---

### 3. **Rutas del Backend**

Las rutas en Flask están registradas con prefijos:

```python
# En app.py
app.register_blueprint(auth_bp, url_prefix='/auth')
```

Esto significa:
- Ruta en auth.py: `@bp.route("/login")`
- URL final: `http://localhost:5001/auth/login`

**Frontend debe usar:**
```javascript
fetch('/auth/login')  // ✅ Correcto (proxy redirige a 5001)
fetch('/api/auth/login')  // ❌ Incorrecto (ruta no existe)
```

---

### 4. **Campos de Login: 'email' vs 'correo'**

El backend acepta ambos campos por compatibilidad:

```python
email = data.get('email') or data.get('correo')
```

**Frontend puede enviar:**
```javascript
// Opción 1
{ "email": "usuario@ejemplo.com", "password": "..." }

// Opción 2
{ "correo": "usuario@ejemplo.com", "password": "..." }
```

Ambos funcionan igual.

---

### 5. **Python 3.13 - Dependencias Específicas**

Este proyecto usa Python 3.13. Algunas dependencias tuvieron que actualizarse:

```txt
gevent==24.11.1        # ✅ Compatible con Python 3.13
# gevent==24.2.1       # ❌ NO compatible

# psycopg2-binary==2.9.9  # ❌ NO compatible (eliminado)
```

**Si agregas nuevas dependencias:**
1. Verifica compatibilidad con Python 3.13
2. Prueba en el entorno virtual
3. Actualiza `requirements.txt`

---

## 🔧 Configuración Detallada

### Variables de Entorno (.env)

```env
# SUPABASE - NO cambiar sin autorización
SUPABASE_URL=https://reubvhoexrkagmtxklek.supabase.co
SUPABASE_KEY=eyJ...  # Anon/Public Key

# JWT - Cambiar en producción
SECRET_KEY=tu_clave_super_secreta_aqui

# REDIS - Opcional (para caché)
REDIS_URL=redis://localhost:6379/0

# FLASK - Debug solo en desarrollo
FLASK_DEBUG=True  # En producción: False
```

### Estructura de la Base de Datos

**Tabla: usuarios**

| Campo | Tipo | Constraints | Ejemplo |
|-------|------|-------------|---------|
| id | int8 | PRIMARY KEY, AUTO INCREMENT | 1 |
| nombre | text | NOT NULL | "CARLOS ALEGRIA" |
| email | text | UNIQUE, NOT NULL | "carlos@ejemplo.com" |
| password | text | NOT NULL | "scrypt:32768:8:1$..." |
| modulos | json | NULL | ["ordenes", "usuarios"] |
| creado_en | timestamptz | DEFAULT now() | "2025-07-01 15:17:00" |

---

## 🎯 Flujo de Autenticación Completo

```
1. Usuario ingresa credenciales en Login.jsx
   └─> { email: "...", password: "..." }

2. Frontend hace fetch a '/auth/login'
   └─> Proxy de Vite redirige a http://localhost:5001/auth/login

3. Backend (auth.py) recibe la petición
   ├─> Valida que email y password existan
   ├─> Busca usuario en Supabase por email
   ├─> Verifica password con check_password_hash()
   └─> Genera token JWT

4. Backend responde con token y datos del usuario
   └─> { success: true, token: "eyJ...", user: {...} }

5. Frontend guarda token en localStorage
   └─> localStorage.setItem('authToken', token)

6. Frontend redirige a la aplicación principal
   └─> onLoginSuccess() ejecutado
```

---

## 🐛 Debugging Tips

### Ver todas las rutas registradas en Flask

```python
# En backend/app.py, agregar temporalmente:
with app.app_context():
    for rule in app.url_map.iter_rules():
        print(f"{rule.methods} → {rule.rule}")
```

### Ver requests en tiempo real (Frontend)

```javascript
// En Login.jsx, antes del fetch:
console.log('Enviando request a:', '/auth/login');
console.log('Datos:', { email, password });

// Después del fetch:
console.log('Response status:', response.status);
console.log('Response data:', data);
```

### Ver logs del backend en tiempo real

```bash
# El script run.py ya muestra los logs, pero si usas run_backend.py:
python run_backend.py | tee backend.log
```

---

## 📊 Métricas y Monitoreo

### Health Check

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

### Verificar conexión a Supabase

```bash
cd nuevo_proyecto
python diagnose.py
```

---

## 🔐 Seguridad - Consideraciones

### Tokens JWT

**Contenido del token:**
```json
{
  "user_id": 1,
  "nombre": "CARLOS ALEGRIA",
  "exp": 1729468800,  // Timestamp de expiración
  "iat": 1729382400   // Timestamp de emisión
}
```

**Validación:**
- El token expira en 24 horas
- Se valida con la misma SECRET_KEY
- No se puede modificar sin invalidarlo

### Ataques Comunes y Protección

| Ataque | Protección Implementada |
|--------|------------------------|
| SQL Injection | ✅ ORM de Supabase |
| XSS | ✅ React sanitiza automáticamente |
| CSRF | ⚠️ Implementar tokens CSRF |
| Brute Force | ⚠️ Implementar rate limiting |
| Man-in-the-Middle | ✅ HTTPS en producción |

---

## 🚀 Despliegue a Producción

### Checklist Pre-Producción

- [ ] Cambiar `FLASK_DEBUG=False`
- [ ] Generar nuevo `SECRET_KEY`
- [ ] Configurar HTTPS
- [ ] Configurar CORS correctamente
- [ ] Implementar rate limiting
- [ ] Configurar logs persistentes
- [ ] Backup de base de datos
- [ ] Monitoreo y alertas

### Variables de Entorno - Producción

```env
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=clave_super_segura_y_larga_generada_aleatoriamente

# Usar variables del hosting
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_KEY=${SUPABASE_KEY}
```

---

## 📞 Contactos de Emergencia

### Si algo se rompe en producción:

1. **Revisar logs:**
   ```bash
   tail -f /var/log/app/error.log
   ```

2. **Rollback rápido:**
   ```bash
   git revert HEAD
   git push origin main
   ```

3. **Reiniciar servicios:**
   ```bash
   systemctl restart app
   ```

4. **Contactar:**
   - DevOps: [contacto]
   - Backend Lead: [contacto]
   - Frontend Lead: [contacto]

---

## 📚 Recursos Adicionales

### Documentación Interna
- `README.md` - Documentación principal
- `CORRECCIONES.md` - Historial de fixes
- `diagnose.py` - Script de diagnóstico

### Herramientas Recomendadas
- **Postman** - Para probar API
- **pgAdmin** - Para gestionar Supabase
- **Redis Commander** - Para gestionar Redis
- **React DevTools** - Para debugging React

---

**Última actualización:** 20 de octubre de 2025  
**Autor:** Equipo de Desarrollo  
**Versión:** 1.0.0


Obtebcion de datos en base de datos de produccion.

📊 Estructura de las Bases de Datos:
Sistema Actual (Supabase)
Tabla: proyectos
ID: id (el ID principal que usamos aquí)
Ejemplo: ID = 30 (BORGOÑO), ID = 55 (ENTEL ARCOS LONGAVÍ)
Sistema de Producción (Nhost)
Tabla 1: proyectos

id = ID local del sistema de producción
nombre = Nombre del proyecto
supabase_proyecto_id = ID del proyecto en Supabase (este es nuestro link!)
Tabla 2: datos_operativos

id_proyecto = ID local (del sistema producción)
venta_total = Monto de producción a sumar
(otros campos...)
🔗 Flujo de Consulta:
Para obtener la "Producción actual" del proyecto con ID_Supabase = 30 (BORGOÑO):

Buscar en Nhost proyectos donde supabase_proyecto_id = 30
→ Obtenemos id_local (ej: 5)

Buscar en Nhost datos_operativos donde id_proyecto = 5
→ Obtenemos todas las filas de producción

Sumar todos los valores de la columna venta_total
→ Este total es la "Producción actual"

Mostrar ese total en el cuadro de "Producción actual" del módulo EstadoPresupuesto
