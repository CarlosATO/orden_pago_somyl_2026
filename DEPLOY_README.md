Build y despliegue - notas rápidas

1) Objetivo
   - Incluir `requirements.txt` fijado en el repo para builds reproducibles.
   - Imagen Docker contiene las libs del sistema necesarias para compilar ruedas nativas (Pillow, psycopg2) y opcionalmente wkhtmltopdf para generación de PDFs.

2) Comandos locales (build + run)

```bash
cd /path/to/seguimiento_ordenes
# construir imagen local
docker build -t seguimiento_ordenes:local .

# correr container (mapear puerto 8080)
docker run -e PORT=8080 -p 8080:8080 seguimiento_ordenes:local
```

3) Variables de entorno necesarias (en Railway / entorno de producción)
   - SUPABASE (instancia cliente o URL+KEY según configuración)
   - SECRET_KEY (Flask secret)
   - DATABASE_URL (si aplica)
   - OTRAS según configuración local: MAIL settings, etc.

4) PDFs (wkhtmltopdf)
   - Dockerfile incluye `wkhtmltopdf` por defecto. Si prefieres desplegar sin wkhtmltopdf, usa `requirements-no-pdf.txt` para generar `requirements.txt` sin pdfkit, y la app ya hace fallback a HTML.

5) Problemas comunes
   - Si el build falla en CI por compilación de wheels: asegurarte que Dockerfile incluya `libjpeg-turbo8-dev`, `zlib1g-dev`, `libpq-dev`, `libxml2-dev`, `libxslt1-dev`, `build-essential`.
   - Usar `pip install --no-cache-dir --prefer-binary -r requirements.txt` para preferir ruedas.

6) Recomendación
   - Mantener `requirements.txt` generado desde un entorno Python 3.12 para reproducibilidad.
