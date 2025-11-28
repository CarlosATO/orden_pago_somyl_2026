# 🚂 Deployment en Railway

## Variables de Entorno Requeridas

Configura las siguientes variables de entorno en Railway:

```env
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=tu_clave_secreta_super_segura_aqui

# Supabase Configuration
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu_supabase_anon_key

# Port (Railway lo configura automáticamente)
PORT=5001
```

## Configuración de Railway

### 1. Crear Nuevo Proyecto
1. Ve a [Railway.app](https://railway.app)
2. Click en "New Project"
3. Selecciona "Deploy from GitHub repo"
4. Conecta tu repositorio

### 2. Configurar Variables de Entorno
En el dashboard de Railway:
1. Ve a la pestaña "Variables"
2. Agrega cada variable de entorno listada arriba
3. Asegúrate de usar valores de producción

### 3. Deploy
Railway detectará automáticamente el `Dockerfile` y construirá la aplicación.

## Correcciones Aplicadas

### ✅ Problemas Resueltos

1. **Case Sensitivity en Imports**
   - Renombrados: `Gastosdirectos.jsx` → `GastosDirectos.jsx`
   - Renombrados: `ordenesPago.jsx` → `OrdenesPago.jsx`
   - Renombrados: `Ordenesnorecepcionadas.jsx` → `OrdenesNoRecepcionadas.jsx`
   - Archivos CSS también renombrados para consistencia

2. **Versión de Node.js**
   - Actualizado de `node:18-alpine` a `node:20-alpine`
   - Vite 7.1.10 requiere Node.js 20.19+ o 22.12+

3. **Configuración de Gunicorn**
   - Corregido el path del módulo en `start.sh`
   - Agregado soporte para variable `PORT` de Railway
   - Configurado timeout y logging para producción

## Estructura del Deploy

```
Railway Build Process:
├── Stage 1: Frontend Builder (Node 20)
│   ├── npm ci (instalar dependencias)
│   └── npm run build (compilar Vite)
│
└── Stage 2: Production Runtime (Python 3.11)
    ├── Instalar dependencias Python
    ├── Copiar backend
    ├── Copiar frontend build → backend/frontend_dist
    └── Ejecutar gunicorn via start.sh
```

## URLs después del Deploy

- **Aplicación Principal**: `https://tu-app.up.railway.app/`
- **Health Check**: `https://tu-app.up.railway.app/api/health`
- **Login API**: `https://tu-app.up.railway.app/auth/login`

## Logs y Debugging

Para ver los logs en Railway:
1. Ve a tu proyecto en Railway
2. Click en la pestaña "Deployments"
3. Selecciona el deployment activo
4. Ve a "View Logs"

## Troubleshooting

### Build Falla en Stage Frontend
- Verifica que todos los imports de componentes tengan capitalización correcta
- Asegúrate de que no haya archivos faltantes

### Runtime Error 500
- Verifica variables de entorno en Railway
- Revisa los logs de Gunicorn
- Asegúrate de que SUPABASE_URL y SUPABASE_KEY sean correctos

### Frontend No Carga
- Verifica que `frontend_dist` fue copiado correctamente
- Asegúrate de que el build de Vite fue exitoso
- Revisa que `app.py` esté sirviendo archivos estáticos

## Comandos Útiles

```bash
# Rebuild local para verificar
docker build -t somyl-app .

# Ejecutar localmente el contenedor
docker run -p 5001:5001 --env-file .env somyl-app

# Ver logs del contenedor
docker logs <container-id>
```

## Next Steps

1. ✅ Hacer commit de los cambios
2. ✅ Push al repositorio
3. ✅ Configurar variables de entorno en Railway
4. ✅ Railway detectará cambios y hará redeploy automático
5. ✅ Verificar deployment en la URL de Railway
