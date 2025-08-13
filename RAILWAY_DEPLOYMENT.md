# Guía de Deployment para Railway

Este documento describe las diferentes opciones para hacer deployment en Railway cuando hay problemas con wkhtmltopdf.

## Problema
El error `wkhtmltopdf` no está disponible en el contenedor base de Railway, causando fallos en el build.

## Soluciones

### Opción 1: Dockerfile Mejorado (Recomendado)
Usar el `Dockerfile` principal que instala wkhtmltopdf desde el repositorio oficial:

```dockerfile
FROM python:3.11-slim

# Actualizar repositorios y agregar repositorio para wkhtmltopdf
RUN apt-get update && \
    apt-get install -y wget gnupg2 ca-certificates lsb-release && \
    wget -qO- https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add -

# Instalar dependencias del sistema incluyendo wkhtmltopdf
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    git \
    fontconfig \
    libfreetype6 \
    libjpeg-dev \
    libpng-dev \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxtst6 \
    libfontconfig1 \
    xvfb && \
    rm -rf /var/lib/apt/lists/*

# Descargar e instalar wkhtmltopdf manualmente
RUN wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.bullseye_amd64.deb && \
    dpkg -i wkhtmltox_0.12.6.1-2.bullseye_amd64.deb || true && \
    apt-get install -f -y && \
    rm wkhtmltox_0.12.6.1-2.bullseye_amd64.deb
```

### Opción 2: Ubuntu Base (Más Simple)
Si la Opción 1 falla, renombrar `Dockerfile.ubuntu` a `Dockerfile`:

```bash
mv Dockerfile Dockerfile.python
mv Dockerfile.ubuntu Dockerfile
```

### Opción 3: Sin PDF (Emergencia)
Si las PDFs no son críticos, usar `Dockerfile.no-pdf` y `requirements-no-pdf.txt`:

```bash
mv Dockerfile Dockerfile.backup
mv Dockerfile.no-pdf Dockerfile
mv requirements.txt requirements.backup
mv requirements-no-pdf.txt requirements.txt
```

## Comandos para Railway

### Para usar Dockerfile específico:
1. En Railway Dashboard > Settings > Deploy
2. Cambiar "Source" a "Dockerfile"
3. Especificar el path del Dockerfile si es necesario

### Variables de entorno necesarias:
```
PORT=8080
FLASK_ENV=production
```

## Testing Local

Para probar cualquier Dockerfile localmente:

```bash
# Opción 1 (Principal)
docker build -t seguimiento-app .

# Opción 2 (Ubuntu)
docker build -f Dockerfile.ubuntu -t seguimiento-app .

# Opción 3 (Sin PDF)
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
- `wkhtmltopdf encontrado en: /usr/local/bin/wkhtmltopdf` (éxito)
- `pdfkit no disponible - PDFs deshabilitados` (fallback)
- `Error generando PDF` (error pero continúa funcionando)

## Recomendación

1. Probar primero con el Dockerfile principal
2. Si falla, usar Dockerfile.ubuntu
3. Como último recurso, usar Dockerfile.no-pdf
