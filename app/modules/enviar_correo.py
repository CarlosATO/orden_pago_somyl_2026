import os
import smtplib
from email.message import EmailMessage
from typing import List, Tuple, Optional

# Cargar variables de entorno solo si estamos en desarrollo
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # En producción (Railway) no necesitamos dotenv
    pass

# Supabase client debe ser pasado desde Flask (current_app.config['SUPABASE'])
def obtener_destinatarios_activos(supabase) -> List[str]:
    """Obtiene los correos activos de la tabla correos_destinatarios en Supabase."""
    rows = (
        supabase.table("correos_destinatarios")
        .select("correo, activo")
        .eq("activo", True)
        .execute()
        .data
    ) or []
    return [row["correo"] for row in rows if row.get("correo")]

def enviar_correo_con_pdfs(
    supabase,
    pdf_principal: Tuple[bytes, str],
    pdf_opcional_1: Optional[Tuple[bytes, str]] = None,
    pdf_opcional_2: Optional[Tuple[bytes, str]] = None,
    asunto: str = "Correo prueba",
    cuerpo: str = "Correo prueba"
):
    """
    Envía un correo con los PDFs adjuntos a los destinatarios activos.
    pdf_principal: (bytes, nombre_archivo)
    pdf_opcional_1/pdf_opcional_2: (bytes, nombre_archivo) o None
    """
    import logging
    logger = logging.getLogger("enviar_correo")
    
    # Verificar variables de entorno con debug completo
    remitente = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_PASS")
    
    # Debug detallado de variables de entorno
    logger.info("=== DEBUG VARIABLES DE ENTORNO ===")
    logger.info(f"Todas las variables disponibles: {list(os.environ.keys())}")
    logger.info(f"GMAIL_USER raw: {repr(os.environ.get('GMAIL_USER'))}")
    logger.info(f"GMAIL_PASS raw: {repr(os.environ.get('GMAIL_PASS'))}")
    logger.info(f"GMAIL_USER valor: {remitente}")
    logger.info(f"GMAIL_PASS presente: {bool(password)}")
    if password:
        logger.info(f"GMAIL_PASS primeros 4 chars: {password[:4]}")
    logger.info("=== FIN DEBUG ===")
    
    # Usar valores por defecto si no están definidos
    if not remitente:
        remitente = "opsomyl@gmail.com"
        logger.warning("Usando GMAIL_USER por defecto")
    
    if not password:
        error_msg = "No se encontró la contraseña de Gmail en el entorno (GMAIL_PASS)"
        logger.error(error_msg)
        raise Exception(error_msg)

    destinatarios = obtener_destinatarios_activos(supabase)
    logger.info(f"Destinatarios activos encontrados: {len(destinatarios)} - {destinatarios}")
    if not destinatarios:
        error_msg = "No hay destinatarios activos en la base de datos"
        logger.error(error_msg)
        raise Exception(error_msg)

    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = remitente
    msg["To"] = ", ".join(destinatarios)
    msg.set_content(cuerpo)

    # Adjuntar PDF principal
    if pdf_principal:
        pdf_bytes, pdf_nombre = pdf_principal
        logger.info(f"Adjuntando PDF principal: {pdf_nombre}")
        msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=pdf_nombre)
    # Adjuntar PDFs opcionales si existen
    for pdf in [pdf_opcional_1, pdf_opcional_2]:
        if pdf:
            pdf_bytes, pdf_nombre = pdf
            logger.info(f"Adjuntando PDF opcional: {pdf_nombre}")
            msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=pdf_nombre)

    # Enviar correo usando SMTP Gmail
    try:
        logger.info(f"Conectando a SMTP Gmail como {remitente}")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(remitente, password)
            smtp.send_message(msg)
        logger.info("Correo enviado correctamente")
    except Exception as e:
        logger.error(f"Error enviando correo: {e}", exc_info=True)
        raise
    return True
