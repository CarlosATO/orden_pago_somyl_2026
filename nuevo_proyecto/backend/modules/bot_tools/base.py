import re
from datetime import datetime
from flask import current_app

def is_db_available(db):
    return db is not None

def safe_generate(model, prompt, default=None):
    """Call the LLM safely with a fallback.
    Returns text or default if model is not configured or call fails.
    """
    if model is None:
        current_app.logger.debug("LLM not configured, returning default")
        return default
    try:
        return model.generate_content(prompt).text.strip()
    except Exception as e:
        current_app.logger.warning(f"LLM generate failed: {e}")
        return default

def format_money(value):
    try:
        v = int(round(float(value)))
        return "${:,.0f}".format(v).replace(",", ".")
    except Exception:
        return str(value)

def extract_order_number(text):
    """Extract an order number (OC) from a text string using regex.
    Returns an int or None.
    """
    if not text:
        return None
    m = re.search(r"\b(?:oc|orden(?: de compra)?|orden_compra|orden_numero)\b[^0-9]*?(\d{1,10})", text, re.I)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None

def format_date_iso(fecha_str):
    if not fecha_str:
        return "Sin fecha"
    try:
        dt = datetime.fromisoformat(fecha_str.replace('Z',''))
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return fecha_str
