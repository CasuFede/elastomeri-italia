"""Test di validazione per la firma e i parametri delle notifiche Telegram."""
import inspect
from services.telegram import invia_notifica_telegram, invia_messaggio_telegram


def test_telegram_notification_signature():
    # Verifica che la funzione accetti i parametri attesi dal router dei preventivi
    sig = inspect.signature(invia_notifica_telegram)
    param_names = list(sig.parameters.keys())
    assert param_names == [
        "nome",
        "email",
        "telefono",
        "servizio",
        "messaggio",
        "token",
        "chat_id",
    ]
