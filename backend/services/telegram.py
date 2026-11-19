"""Servizio di notifica su bot Telegram."""
import html
import json
from datetime import datetime, timezone
from typing import Any, Optional


async def invia_messaggio_telegram(
    token: Optional[str],
    chat_id: Optional[str],
    testo_messaggio: str,
) -> None:
    if not token or not chat_id:
        print("Credenziali Telegram mancanti nei secrets del Worker.")
        return

    if len(testo_messaggio) > 3900:
        testo_messaggio = (
            testo_messaggio[:3800]
            + "\n\n<i>[Messaggio troncato per limiti di lunghezza Telegram]</i>"
        )
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": testo_messaggio,
        "parse_mode": "HTML",
    }

    try:
        try:
            from pyodide.http import pyfetch

            response = await pyfetch(
                url,
                method="POST",
                headers={"content-type": "application/json"},
                body=json.dumps(payload),
            )
            if not response.ok:
                print(f"Errore durante l'invio a Telegram: HTTP {response.status}")
        except ImportError:
            try:
                import urllib.request

                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10):
                    pass
            except Exception:
                from js import Object, fetch
                from pyodide.ffi import to_js

                headers_js = to_js({"content-type": "application/json"}, dict_converter=Object.fromEntries)
                options = to_js(
                    {
                        "method": "POST",
                        "headers": headers_js,
                        "body": json.dumps(payload),
                    },
                    dict_converter=Object.fromEntries,
                )
                response = await fetch(url, options)
                if not response.ok:
                    print(f"Errore durante l'invio a Telegram: HTTP {response.status}")
    except BaseException as exc:
        print(f"Errore durante l'invio a Telegram: {exc}")


async def invia_notifica_telegram(
    nome: str,
    email: str,
    telefono: str,
    servizio: str,
    messaggio: str,
    token: Optional[str],
    chat_id: Optional[str],
) -> None:
    testo_messaggio = (
        f"🚀 <b>Nuovo Preventivo Poliurea System!</b>\n\n"
        f"👤 <b>Nome:</b> {html.escape(nome)}\n"
        f"📧 <b>Email:</b> {html.escape(email)}\n"
        f"📞 <b>Telefono:</b> {html.escape(telefono)}\n"
        f"🛠 <b>Servizio:</b> {html.escape(servizio)}\n"
        f"💬 <b>Messaggio:</b>\n{html.escape(messaggio or 'Nessun messaggio specificato')}"
    )
    await invia_messaggio_telegram(token, chat_id, testo_messaggio)


async def invia_notifica_recupero_telegram(
    nome: str,
    email: str,
    token: Optional[str],
    chat_id: Optional[str],
) -> None:
    adesso = datetime.now(timezone.utc).strftime("%d/%m/%Y alle %H:%M UTC")
    testo_messaggio = (
        f"🔐 <b>Richiesta Recupero Password Area Clienti</b>\n\n"
        f"👤 <b>Cliente:</b> {html.escape(nome)}\n"
        f"📧 <b>Email:</b> {html.escape(email)}\n"
        f"⏰ <b>Data:</b> {adesso}\n\n"
        f"ℹ️ <i>Il cliente ha richiesto il ripristino delle credenziali di accesso. Accedi alla scheda 'Account clienti' nel pannello Admin per reimpostare la sua password.</i>"
    )
    await invia_messaggio_telegram(token, chat_id, testo_messaggio)
