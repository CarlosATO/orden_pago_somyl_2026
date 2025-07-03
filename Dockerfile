FROM python:3.11-slim

# Instala dependencias del sistema necesarias para wkhtmltopdf, pdfkit y git
RUN apt-get update && \
    apt-get install -y wkhtmltopdf build-essential libssl-dev libffi-dev git && \
    rm -rf /var/lib/apt/lists/*

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
CMD ["gunicorn", "run:app", "--bind", "0.0.0.0:8080"]