# 🚀 Guía Rápida de Inicio

## Para Nuevos Desarrolladores

### ⚡ Inicio en 3 Pasos

```bash
# 1. Activar entorno virtual
source /Users/carlosalegria/Desktop/Migracion_OP/.venv/bin/activate

# 2. Iniciar sistema completo
run.py

# 3. Abrir en el navegador
# → http://localhost:5173
```

¡Eso es todo! 🎉

---

## 📋 Lo Esencial

### Comandos Básicos

| Comando | Descripción |
|---------|-------------|
| `run.py` | Inicia backend + frontend |
| `Ctrl+C` | Detiene todo el sistema |
| `lsof -ti:5001,5173 \| xargs kill -9` | Libera puertos |
| `python diagnose.py` | Verifica estado del backend |

### URLs Importantes

| Servicio | URL |
|----------|-----|
| **Frontend** | http://localhost:5173 |
| **Backend** | http://localhost:5001 |
| **Login API** | http://localhost:5001/auth/login |
| **Health** | http://localhost:5001/api/health |

### Credenciales de Prueba

```
Email: carlosalegria@me.com
Password: camilo
```

---

## 🔥 Puntos Clave

### ⚠️ IMPORTANTE

1. **Contraseñas:** Usar `werkzeug.security`, NO bcrypt
2. **Proxy:** Configurado en `vite.config.js`
3. **Rutas:** `/auth/login` (NO `/api/auth/login`)
4. **Python:** Versión 3.13 requerida
5. **Reiniciar:** Vite necesita reinicio después de cambios en config

### ✅ Lo que Funciona

- ✅ Login con JWT
- ✅ Conexión a Supabase
- ✅ Hot reload (frontend)
- ✅ Auto-restart (backend)
- ✅ Proxy Vite funcionando

### 📂 Archivos Clave

```
nuevo_proyecto/
├── run.py              # 🎯 INICIO AQUÍ
├── .env                # 🔐 Variables de entorno
├── backend/
│   ├── app.py          # Configuración Flask
│   └── modules/
│       └── auth.py     # Login endpoint
└── frontend/
    ├── vite.config.js  # Proxy config
    └── src/
        └── components/
            └── Login.jsx
```

---

## 🐛 Problemas Comunes

| Problema | Solución |
|----------|----------|
| Error 404 en login | Reiniciar Vite + recargar navegador |
| Puerto ocupado | `lsof -ti:5001,5173 \| xargs kill -9` |
| "Invalid salt" | Verificar que use werkzeug, no bcrypt |
| Proxy no funciona | Verificar `vite.config.js` + reiniciar |

---

## 📚 Documentación Completa

- **README.md** - Documentación completa del sistema
- **NOTAS_DESARROLLADORES.md** - Notas técnicas detalladas
- **CORRECCIONES.md** - Historial de correcciones

---

## 🆘 Ayuda Rápida

```bash
# Backend no inicia
cd nuevo_proyecto && python diagnose.py

# Ver errores
tail -f logs/error.log

# Probar login
cd nuevo_proyecto && python test_login.py

# Reinstalar dependencias
pip install -r backend/requirements.txt
cd frontend && npm install
```

---

**¿Dudas?** Revisa `README.md` para información completa.

**¿Login no funciona?** Lee `CORRECCIONES.md` - todos los problemas están documentados.

---

✨ **Hecho con ❤️ por el equipo de desarrollo**
