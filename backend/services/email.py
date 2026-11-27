"""Servizio per l'invio delle email di notifica, conferma preventivo e credenziali."""
import json
import logging
from typing import Any

from core.config import get_secret, is_worker_runtime, maschera_email
from schemas.preventivi import PreventivoRequest
from services.email_templates import (
    build_chiarimenti_preventivo_email,
    build_conferma_preventivo_email,
    build_credenziali_cliente_email,
    build_recupero_password_email,
)

logger = logging.getLogger("poliurea.email")


async def esegui_http_post(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> bool:
    """Esegue una chiamata POST HTTP compatibile sia con Pyodide (Wasm) sia con standard Python."""
    try:
        try:
            from pyodide.http import pyfetch

            response = await pyfetch(
                url,
                method="POST",
                headers=headers,
                body=json.dumps(payload),
            )
            return response.ok
        except ImportError:
            try:
                import urllib.request

                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return 200 <= resp.status < 300
            except Exception:
                from js import Object, fetch
                from pyodide.ffi import to_js

                headers_js = to_js(headers, dict_converter=Object.fromEntries)
                options = to_js(
                    {
                        "method": "POST",
                        "headers": headers_js,
                        "body": json.dumps(payload),
                    },
                    dict_converter=Object.fromEntries,
                )
                res = await fetch(url, options)
                return res.ok
    except Exception as exc:
        logger.warning("Errore invio HTTP POST a %s: %s", url, type(exc).__name__)
        return False


async def _invia_via_brevo(
    brevo_key: str,
    smtp_from_name: str,
    smtp_from_email: str,
    to_email: str,
    to_nome: str,
    subject: str,
    html_content: str,
    text_content: str,
) -> bool:
    payload = {
        "sender": {"name": smtp_from_name, "email": smtp_from_email},
        "to": [{"email": to_email, "name": to_nome}],
        "subject": subject,
        "htmlContent": html_content,
        "textContent": text_content,
    }
    headers = {
        "api-key": brevo_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    return await esegui_http_post("https://api.brevo.com/v3/smtp/email", headers, payload)


async def invia_email(
    to_email: str,
    to_nome: str,
    subject: str,
    html_content: str,
    text_content: str,
    environment: Any,
) -> bool:
    """Invia email tramite Brevo API (Cloudflare Workers) o SMTP diretto in ambiente locale."""
    smtp_server = get_secret(environment, "SMTP_SERVER")
    smtp_port_val = get_secret(environment, "SMTP_PORT") or "465"
    smtp_user = get_secret(environment, "SMTP_USER")
    smtp_password = get_secret(environment, "SMTP_PASSWORD")
    smtp_from_email = get_secret(environment, "SMTP_FROM_EMAIL") or "info@poliureasystem.it"
    smtp_from_name = get_secret(environment, "SMTP_FROM_NAME") or "Poliurea System"
    destinatario_log = maschera_email(to_email)

    brevo_key = get_secret(environment, "BREVO_API_KEY")

    # 1. Su Cloudflare Workers (Wasm/Pyodide) usa Brevo REST API
    if is_worker_runtime():
        if brevo_key and await _invia_via_brevo(
            brevo_key,
            smtp_from_name,
            smtp_from_email,
            to_email,
            to_nome,
            subject,
            html_content,
            text_content,
        ):
            logger.info("[BREVO OK] Email inviata a %s", destinatario_log)
            return True
        logger.warning("[EMAIL WARNING] Provider email non configurato/fallito per %s", destinatario_log)
        return False

    # 2. Invio tramite SMTP diretto in ambiente Python locale
    if smtp_server and smtp_user and smtp_password:
        from email.header import Header
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.utils import formataddr
        import smtplib

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = Header(subject, "utf-8")
            msg["From"] = formataddr((str(Header(smtp_from_name, "utf-8")), smtp_from_email))
            msg["To"] = formataddr((str(Header(to_nome, "utf-8")), to_email))
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            smtp_port = int(smtp_port_val)
            if smtp_port == 465:
                import ssl

                ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_server, smtp_port, context=ctx, timeout=10) as s:
                    s.login(smtp_user, smtp_password)
                    s.send_message(msg)
            else:
                with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as s:
                    s.ehlo()
                    try:
                        s.starttls()
                        s.ehlo()
                    except Exception:
                        pass
                    s.login(smtp_user, smtp_password)
                    s.send_message(msg)
            logger.info("[SMTP DIRECT OK] Email inviata a %s", destinatario_log)
            return True
        except Exception as smtp_exc:
            logger.warning("[SMTP FALLBACK] Errore invio diretto (%s), tento Brevo", type(smtp_exc).__name__)

    # 3. Fallback su Brevo API se configurato in locale
    if brevo_key and await _invia_via_brevo(
        brevo_key,
        smtp_from_name,
        smtp_from_email,
        to_email,
        to_nome,
        subject,
        html_content,
        text_content,
    ):
        logger.info("[BREVO OK] Email inviata a %s", destinatario_log)
        return True

    logger.warning("[EMAIL WARNING] Nessun provider email disponibile per %s", destinatario_log)
    return False


async def invia_email_conferma_preventivo(
    dati: PreventivoRequest,
    id_preventivo: int,
    totale_foto: int,
    environment: Any,
) -> None:
    """Invia email di conferma richiesta preventivo al cliente."""
    subject, html_content, text_content = build_conferma_preventivo_email(
        dati, id_preventivo, totale_foto
    )
    await invia_email(
        to_email=str(dati.email),
        to_nome=dati.nome,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        environment=environment,
    )


async def invia_email_credenziali_cliente(
    nome: str,
    email: str,
    password_temporanea: str,
    environment: Any,
) -> None:
    """Invia email con credenziali di primo accesso per l'Area Clienti."""
    subject, html_content, text_content = build_credenziali_cliente_email(
        nome, email, password_temporanea
    )
    await invia_email(
        to_email=email,
        to_nome=nome,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        environment=environment,
    )


async def invia_email_recupero_password_cliente(
    nome: str,
    email: str,
    reset_url: str,
    environment: Any,
) -> None:
    """Invia email con link monouso (30 min) per il recupero password dimenticata."""
    subject, html_content, text_content = build_recupero_password_email(
        nome, email, reset_url
    )
    await invia_email(
        to_email=email,
        to_nome=nome,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        environment=environment,
    )


async def invia_email_chiarimenti_preventivo(
    nome: str,
    email: str,
    preventivo_id: int,
    servizio: str,
    messaggio_chiarimenti: str,
    environment: Any,
) -> None:
    """Invia email al cliente con note o chiarimenti inseriti dall'amministratore."""
    subject, html_content, text_content = build_chiarimenti_preventivo_email(
        nome, preventivo_id, servizio, messaggio_chiarimenti
    )
    await invia_email(
        to_email=str(email),
        to_nome=nome,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        environment=environment,
    )


# Alias per retrocompatibilità
invia_email_reset_password_cliente = invia_email_recupero_password_cliente
