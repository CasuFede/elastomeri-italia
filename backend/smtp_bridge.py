#!/usr/bin/env python3
"""
SMTP Bridge per Poliurea System.
Servizio HTTP locale leggero (standard library) per spedire email autenticate
tramite Aruba SMTPS (smtps.aruba.it:465) aggirando le limitazioni di socket
di Pyodide / workerd in ambiente locale/container.
"""

import json
import logging
import os
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SMTP_BRIDGE] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

DEFAULT_SERVER = os.environ.get("SMTP_SERVER", "smtps.aruba.it")
DEFAULT_PORT = int(os.environ.get("SMTP_PORT", 465))
DEFAULT_USER = os.environ.get("SMTP_USER", "")
DEFAULT_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", os.environ.get("SMTP_USER", "info@poliureasystem.it"))
DEFAULT_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "Poliurea System")


def spedisci_email(dati: dict) -> tuple[bool, str]:
    to_email = dati.get("to_email", "").strip()
    if not to_email:
        return False, "Email destinatario mancante."

    to_nome = dati.get("to_nome", "")
    subject = dati.get("subject", "Notifica Poliurea System")
    html_content = dati.get("html_content") or dati.get("htmlContent") or ""
    text_content = dati.get("text_content") or dati.get("textContent") or ""

    smtp_server = dati.get("smtp_server") or DEFAULT_SERVER
    smtp_port = int(dati.get("smtp_port") or DEFAULT_PORT)
    smtp_user = dati.get("smtp_user") or DEFAULT_USER
    smtp_password = dati.get("smtp_password") or DEFAULT_PASSWORD
    smtp_from_email = dati.get("smtp_from_email") or DEFAULT_FROM_EMAIL
    smtp_from_name = dati.get("smtp_from_name") or DEFAULT_FROM_NAME

    if not smtp_user or not smtp_password:
        logging.error("Tentativo di invio email fallito: credenziali SMTP non configurate nell'ambiente.")
        return False, "Credenziali SMTP non configurate nell'ambiente."

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header(smtp_from_name, "utf-8")), smtp_from_email))
    msg["To"] = formataddr((str(Header(to_nome, "utf-8")), to_email)) if to_nome else to_email
    msg["Reply-To"] = smtp_from_email

    if text_content:
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
    if html_content:
        msg.attach(MIMEText(html_content, "html", "utf-8"))

    context = ssl.create_default_context()
    tentativi = [smtp_port]
    if smtp_port == 465 and 587 not in tentativi:
        tentativi.append(587)
    elif smtp_port == 587 and 465 not in tentativi:
        tentativi.append(465)

    ultimo_errore = ""
    for p in tentativi:
        try:
            if p == 465:
                with smtplib.SMTP_SSL(smtp_server, p, context=context, timeout=12) as s:
                    s.login(smtp_user, smtp_password)
                    s.send_message(msg)
            else:
                with smtplib.SMTP(smtp_server, p, timeout=12) as s:
                    s.ehlo("poliureasystem.it")
                    s.starttls(context=context)
                    s.ehlo("poliureasystem.it")
                    s.login(smtp_user, smtp_password)
                    s.send_message(msg)

            logging.info(f"Email inviata con successo via {smtp_server}:{p} a {to_email} (Oggetto: {subject})")
            return True, "Email inviata con successo."
        except Exception as exc:
            ultimo_errore = f"{type(exc).__name__}: {exc}"
            logging.warning(f"Tentativo via {smtp_server}:{p} fallito: {ultimo_errore}")

    return False, f"Tutti i tentativi falliti. Ultimo errore: {ultimo_errore}"


class SmtpBridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # silenzia log standard http
        pass

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "smtp-bridge"})
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        if self.path == "/send-email":
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception as e:
                self._send_json(400, {"status": "error", "detail": f"JSON non valido: {e}"})
                return

            ok, msg = spedisci_email(payload)
            if ok:
                self._send_json(200, {"status": "success", "message": msg})
            else:
                self._send_json(500, {"status": "error", "detail": msg})
        else:
            self._send_json(404, {"error": "Not Found"})


def run():
    port = 8025
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, SmtpBridgeHandler)
    logging.info(f"SMTP Bridge avviato su http://127.0.0.1:{port} (solo interfaccia locale protetta)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()


if __name__ == "__main__":
    run()
