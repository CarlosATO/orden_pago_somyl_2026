# Guía de Deployment para Railway

Este documento describe las diferentes opciones para hacer deployment en Railway cuando hay problemas con wkhtmltopdf.

## Problema
El error `wkhtmltopdf` no está disponible en el contenedor base de Railway, causando fallos en el build.

## Soluciones (Por Orden de Preferencia)

### Opción 1: Ubuntu Base (Actual - Recomendado) ✅
Usar el `Dockerfile` principal que usa Ubuntu 22.04:

```dockerfile
FROM ubuntu:22.04

# Evitar prompts interactivos durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instalar Python y dependencias del sistema
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    wkhtmltopdf \
    build-essential \
    libssl-dev \
    libffi-dev \
    git \
    xvfb \
    && rm -rf /var/lib/apt/lists/*
```

**Ventajas:**
- wkhtmltopdf disponible directamente en repositorios de Ubuntu
- Instalación más confiable
- Imagen más estable

### Opción 2: Dockerfile Complejo (Fallback)
Si la Opción 1 falla, usar `Dockerfile.complex`:

```bash
mv Dockerfile Dockerfile.ubuntu
mv Dockerfile.complex Dockerfile
```

### Opción 3: Dockerfile Minimal (Sin PDF)
Para deployment rápido sin funcionalidad PDF:

```bash
mv Dockerfile Dockerfile.backup
mv Dockerfile.minimal Dockerfile
mv requirements.txt requirements.backup
mv requirements-no-pdf.txt requirements.txt
```

### Opción 4: Sin PDF Completo (Emergencia)
Si todo falla, usar `Dockerfile.no-pdf`:

```bash
mv Dockerfile Dockerfile.backup
mv Dockerfile.no-pdf Dockerfile
mv requirements.txt requirements.backup
mv requirements-no-pdf.txt requirements.txt
```

## Jerarquía de Archivos

```
Dockerfile              ← Ubuntu 22.04 (ACTUAL)
Dockerfile.complex      ← Python slim + instalación manual wkhtmltopdf  
Dockerfile.minimal      ← Python slim básico (sin wkhtmltopdf)
Dockerfile.no-pdf       ← Python slim sin dependencias PDF
Dockerfile.ubuntu       ← Backup del Ubuntu original

requirements.txt        ← Con pdfkit
requirements-no-pdf.txt ← Sin pdfkit
```

## Comandos para Railway

### Para usar Dockerfile específico:
1. En Railway Dashboard > Settings > Deploy
2. Cambiar "Source" a "Dockerfile"
3. Railway automáticamente usará el `Dockerfile` en la raíz

### Variables de entorno necesarias:
```
PORT=8080
FLASK_ENV=production
```

## Testing Local

Para probar cualquier Dockerfile localmente:

```bash
# Opción 1 (Actual - Ubuntu)
docker build -t seguimiento-app .

# Opción 2 (Complejo)
docker build -f Dockerfile.complex -t seguimiento-app .

# Opción 3 (Minimal)
docker build -f Dockerfile.minimal -t seguimiento-app .

# Opción 4 (Sin PDF)
docker build -f Dockerfile.no-pdf -t seguimiento-app .

# Ejecutar
docker run -p 8080:8080 seguimiento-app
```

## Verificación de Funcionamiento

La aplicación incluye manejo automático de fallback:

1. **Con wkhtmltopdf**: Genera PDFs normalmente
2. **Sin wkhtmltopdf**: Funciona sin generar PDFs, muestra advertencias en logs

## Logs útiles

En Railway, revisar logs para:
- `wkhtmltopdf encontrado en: /usr/bin/wkhtmltopdf` (éxito)
- `pdfkit no disponible - PDFs deshabilitados` (fallback)
- `Error generando PDF` (error pero continúa funcionando)

## Estrategia de Resolución

1. ✅ **Intentar con Ubuntu** (Dockerfile actual)
2. Si falla → **Dockerfile.complex**
3. Si falla → **Dockerfile.minimal** 
4. Si falla → **Dockerfile.no-pdf** + requirements-no-pdf.txt

## Estado Actual
- **Dockerfile principal**: Ubuntu 22.04 con wkhtmltopdf nativo
- **Aplicación**: Robusta con fallbacks automáticos
- **Probabilidad de éxito**: Alta ✅
