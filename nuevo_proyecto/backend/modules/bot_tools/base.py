import re
from datetime import datetime
def is_db_available(db):
    """Verifica si la conexión a la BD es válida."""
    return db is not None

def safe_generate(model, prompt, default=None):
    """Envía un prompt a Gemini de forma segura."""
    if not model:
        return default
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Error IA: {e}")
        return default

def format_money(value):
    """Formatea números a dinero chileno (CLP)."""
    try:
        val = float(value or 0)
        return "${:,.0f}".format(val).replace(",", ".")
    except:
        return "$0"

def format_date_iso(date_str):
    """Convierte fecha ISO a DD/MM/YYYY."""
    if not date_str: return "S/F"
    try:
        # Intenta cortar la parte de la hora si viene con T
        clean_date = str(date_str).split('T')[0]
        dt = datetime.strptime(clean_date, '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except:
        return str(date_str)

def extract_order_number(text):
    """Busca un número de orden en el texto."""
    match = re.search(r'(?:oc|orden|pedido|#)\s*[:#-]?\s*(\d+)', text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None