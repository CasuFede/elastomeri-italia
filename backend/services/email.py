"""Servizio per l'invio delle email di notifica, conferma preventivo e credenziali."""
import json
from typing import Any

from core.config import get_secret
from schemas.preventivi import PreventivoRequest
from services.email_templates import (
    build_chiarimenti_preventivo_email,
    build_conferma_preventivo_email,
    build_credenziali_cliente_email,
    build_recupero_password_email,
)


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
        print(f"Errore invio HTTP POST a {url}: {exc}")
        return False


async def invia_email(
    to_email: str,
    to_nome: str,
    subject: str,
    html_content: str,
    text_content: str,
    environment: Any,
) -> bool:
    """Invia email tramite SMTP Bridge locale (Aruba SMTPS) o fallback su Brevo API."""
    smtp_server = get_secret(environment, "SMTP_SERVER")
    smtp_port_val = get_secret(environment, "SMTP_PORT") or "465"
    smtp_user = get_secret(environment, "SMTP_USER")
    smtp_password = get_secret(environment, "SMTP_PASSWORD")
    smtp_from_email = get_secret(environment, "SMTP_FROM_EMAIL") or "info@poliureasystem.it"
    smtp_from_name = get_secret(environment, "SMTP_FROM_NAME") or "Poliurea System"

    import sys
    is_worker_env = sys.platform == "emscripten" or "pyodide" in sys.modules

    # 1. Se su Cloudflare Worker (Wasm/Pyodide), le socket TCP grezze non sono permesse:
    # l'invio deve avvenire tramite API HTTP REST (Brevo API).
    brevo_key = get_secret(environment, "BREVO_API_KEY")
    if is_worker_env:
        if brevo_key:
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
            ok_brevo = await esegui_http_post("https://api.brevo.com/v3/smtp/email", headers, payload)
            if ok_brevo:
                print(f"[BREVO EMAIL OK] Email inviata con successo via Brevo API a {to_email}")
                return True
        print(f"[EMAIL WARNING] Nessun provider email HTTP valido configurato per Cloudflare Workers (destinatario: {to_email})")
        return False

    # 2. Bridge SMTP locale dedicato (solo in ambiente locale/container dove la porta 8025 è attiva)
    if smtp_server and smtp_user and smtp_password:
        bridge_payload = {
            "to_email": to_email,
            "to_nome": to_nome,
            "subject": subject,
            "html_content": html_content,
            "text_content": text_content,
            "smtp_server": smtp_server,
            "smtp_port": int(smtp_port_val or 465),
            "smtp_user": smtp_user,
            "smtp_password": smtp_password,
            "smtp_from_email": smtp_from_email,
            "smtp_from_name": smtp_from_name,
        }
        try:
            ok_bridge = await esegui_http_post(
                "http://127.0.0.1:8025/send-email",
                {"Content-Type": "application/json"},
                bridge_payload,
            )
            if ok_bridge:
                print(f"[ARUBA SMTP EMAIL OK] Email inviata con successo via Bridge Aruba a {to_email}")
                return True
        except Exception as bridge_err:
            print(f"[ARUBA SMTP BRIDGE NOTE] Bridge 8025 non attivo: {bridge_err}")

    # 3. Invio tramite SMTP diretto (se Python nativo con socket supportati)
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
            print(f"[SMTP DIRECT EMAIL OK] Email inviata con successo via Aruba SMTPS a {to_email}")
            return True
        except Exception as smtp_exc:
            print(f"[SMTP DIRECT FALLBACK] Invio SMTP diretto non riuscito ({smtp_exc}), tento fallback...")

    # 2. Fallback su Brevo API se configurato
    brevo_key = get_secret(environment, "BREVO_API_KEY")
    if brevo_key:
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
        ok_brevo = await esegui_http_post("https://api.brevo.com/v3/smtp/email", headers, payload)
        if ok_brevo:
            print(f"[BREVO EMAIL OK] Email inviata con successo via Brevo API a {to_email}")
            return True

    print(f"[EMAIL WARNING] Nessun provider email disponibile o configurato per l'invio a {to_email}")
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
