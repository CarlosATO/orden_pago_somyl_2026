from flask import current_app
from .base import is_db_available, safe_generate, format_money

def procesar_consulta(texto_usuario, db, model=None):
    """Responde consultas sobre materiales: buscar por código o nombre y devolver ficha breve.
    Ejemplos:
      - "Material COD123"
      - "Precio de cemento" (si existe precio en tabla)
      - "Buscar material arena" 
    """
    try:
        if not is_db_available(db):
            return "No hay base de datos disponible para buscar materiales."

        # Intentar extraer palabra clave con LLM si disponible
        prompt = f"Extrae SOLO la palabra clave del material en: '{texto_usuario}'"
        material_key = safe_generate(model, prompt, default=None) or ''
        if not material_key:
            # fallback: tomar la última palabra si la frase contiene 'material' o 'precio'
            parts = texto_usuario.split()
            material_key = parts[-1] if parts else ''

        material_key = material_key.strip().replace('"', '').replace("'", "")
        if not material_key:
            return "No entendí el material. Indica el nombre o código (ej: 'Material M123' o 'Cemento')."

        res = db.table('materiales').select('*').or_(f"cod.ilike.%{material_key}%,material.ilike.%{material_key}%").limit(5).execute()
        if not res.data:
            return f"No encontré materiales que coincidan con '{material_key}'."

        # presentar hasta 5 resultados breves
        results = []
        for m in res.data:
            cod = m.get('cod') or 'S/COD'
            nombre = m.get('material') or 'Sin nombre'
            tipo = m.get('tipo') or ''
            # precio si existe
            precio = m.get('precio')
            precio_txt = f" - Precio: {format_money(precio)}" if precio else ""
            results.append(f"{cod} | {nombre} {f'({tipo})' if tipo else ''}{precio_txt}")

        if len(results) == 1:
            return f"Ficha material:\n{results[0]}"
        else:
            return "Resultados:\n" + "\n".join(results)

    except Exception as e:
        current_app.logger.exception(f"Error en chat_materiales: {e}")
        return "Error consultando materiales."
