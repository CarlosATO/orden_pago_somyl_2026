FROM ubuntu:22.04

# Evitar prompts interactivos durante la instalación
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
    libpq-dev \
    zlib1g-dev \
    libjpeg-dev \
    libxml2-dev \
    libxslt1-dev \
    git \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Crear alias para python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar solo requirements esenciales primero
COPY requirements-no-pdf.txt ./requirements.txt

# Copiar el resto de archivos
COPY . .

# Instalar las dependencias de Python (versión simplificada sin numpy/pandas)
RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install -r requirements.txt

# Exponer el puerto (Railway usará la variable $PORT)
EXPOSE 8080

# Comando de inicio
CMD ["sh", "-c", "gunicorn run:app --bind 0.0.0.0:$PORT"]
