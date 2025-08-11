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
    
    # Cargar variables de entorno de manera robusta
    # Prioridad: 1) Variables de entorno del sistema, 2) Variables por defecto
    remitente = os.environ.get("GMAIL_USER") or os.getenv("GMAIL_USER") or "opsomyl@gmail.com"
    password = os.environ.get("GMAIL_PASS") or os.getenv("GMAIL_PASS") or "nwak xdzx vdor uizh"
    
    # Logging para confirmar que todo está bien
    logger.info(f"✅ Gmail configurado - Usuario: {remitente}")
    logger.info(f"✅ Gmail password configurado: {bool(password)}")
    
    # Debug para Railway (mantener por si acaso)
    gmail_user_env = os.environ.get("GMAIL_USER")
    gmail_pass_env = os.environ.get("GMAIL_PASS")
    if gmail_user_env:
        logger.info("✅ GMAIL_USER encontrado en os.environ")
    else:
        logger.info("⚠️ GMAIL_USER no encontrado en os.environ, usando fallback")
    
    if gmail_pass_env:
        logger.info("✅ GMAIL_PASS encontrado en os.environ")
    else:
        logger.info("⚠️ GMAIL_PASS no encontrado en os.environ, usando fallback")
    
    if not password:
        error_msg = "No se pudo configurar las credenciales de Gmail"
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
