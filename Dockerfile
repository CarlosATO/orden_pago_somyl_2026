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

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos del proyecto
COPY . .

# Instala las dependencias de Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expone el puerto (Railway usará la variable $PORT)
EXPOSE 8080

# Comando de inicio
CMD ["sh", "-c", "gunicorn run:app --bind 0.0.0.0:$PORT"]