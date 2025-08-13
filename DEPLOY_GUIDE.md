# Guía de Deployment - Seguimiento de Órdenes

## Estado Actual del Deployment 🚀

### Railway Deployment - Estrategia Simplificada
✅ **Dockerfile Simple Activo**: Sin numpy/pandas problemáticos
✅ **requirements-no-pdf.txt**: Dependencias mínimas y estables
✅ **Aplicación Resiliente**: Imports opcionales de pandas

#### Estrategia Actual:
1. **Dockerfile**: Simple con wkhtmltopdf pero sin librerías matemáticas pesadas
2. **Dependencies**: requirements-no-pdf.txt (sin numpy/pandas)
3. **Código**: Imports opcionales de pandas con graceful degradation

#### Para Deploying:
```bash
# Ya configurado - solo hacer push
git add .
git commit -m "Simplified deployment strategy"
git push
```

### Funcionalidad Afectada:
- ❌ **Análisis avanzado de datos** en presupuestos (requiere pandas)
- ✅ **Funcionalidad básica completa** mantenida
- ✅ **PDF generation** funcional con wkhtmltopdf
- ✅ **Toda la lógica de negocio** intacta

## Archivos de Configuración

### Dockerfile Principal (Activo)
```dockerfile
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# Instalar Python y dependencias básicas
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    wkhtmltopdf \
    build-essential \
    libssl-dev \
    libffi-dev \
    git \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Usar requirements simplificados
COPY requirements-no-pdf.txt ./requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Resto de la configuración...
```

### requirements-no-pdf.txt (Activo)
Dependencias optimizadas sin librerías problemáticas:
- Flask stack básico
- Supabase client
- Utilidades de fecha/tiempo
- Sin numpy, pandas, scipy

## Estrategias de Fallback

### Opción 1: Dockerfile Completo
Si necesitas pandas:
```bash
mv Dockerfile Dockerfile.simple
mv Dockerfile.ubuntu-complex Dockerfile
mv requirements-no-pdf.txt requirements-no-pdf.backup
mv requirements.txt requirements-active.txt
```

### Opción 2: Deployment Minimal
Sin wkhtmltopdf:
```bash
mv Dockerfile Dockerfile.backup
mv Dockerfile.minimal Dockerfile
```

## Código Resiliente

### Imports Opcionales Implementados
```python
# En presupuestos.py y estado_presupuesto.py
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Uso condicional
if PANDAS_AVAILABLE:
    # Funcionalidad avanzada con pandas
else:
    # Funcionalidad básica sin pandas
```

## Variables de Entorno (Railway)

```env
SUPABASE_URL=tu_supabase_url
SUPABASE_KEY=tu_supabase_key
SECRET_KEY=tu_secret_key_flask
FLASK_ENV=production
FLASK_DEBUG=False
```

## Verificación Post-Deployment

1. **Health Check**: Verificar que la app inicie
2. **Login**: Probar autenticación
3. **CRUD Básico**: Crear/editar órdenes
4. **PDF**: Generar PDFs (si wkhtmltopdf disponible)
5. **Features**: Verificar módulos principales

## Troubleshooting

### Si el build falla en Railway:
1. Verificar logs de build en Railway dashboard
2. Probar con Dockerfile.minimal
3. Revisar requirements-no-pdf.txt

### Si la app no inicia:
1. Verificar variables de entorno
2. Checkear logs de aplicación
3. Validar conectividad a Supabase

### Si faltan features:
1. Confirmar que imports opcionales funcionan
2. Verificar mensajes en logs sobre librerías faltantes
3. Considerar upgrade a Dockerfile completo

## Próximos Pasos

1. **Monitorear** el deployment actual
2. **Optimizar** si es necesario
3. **Documentar** cualquier issue
4. **Considerar** re-habilitar pandas cuando Railway mejore el build process
