"""Configurazioni di base e costanti di sistema."""
import os
import re
from typing import Any, Optional

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
MAX_UPLOAD_COUNT = 5
PASSWORD_ITERATIONS = 100_000
TOKEN_SESSIONE_DURATA = 8 * 3600  # 8 ore
TELEFONO_REGEX = re.compile(r"^\+?[0-9\s\-\.\(\)]{6,25}$")

STATI_PREVENTIVO = {
    "ricevuto": "Ricevuto",
    "in_valutazione": "In valutazione",
    "preventivo_inviato": "Preventivo inviato",
    "in_lavorazione": "In lavorazione",
    "completato": "Completato",
    "annullato": "Annullato",
}

COLONNE_LAVORO_VALIDE = {
    "titolo": 160,
    "descrizione": 2000,
    "localita": 120,
}


def get_secret(environment: Any, key: str) -> Optional[str]:
    from typing import Optional
    if environment is not None:
        try:
            valore = getattr(environment, key, None)
            if valore is not None:
                return str(valore).strip()
        except Exception:
            pass
    return os.environ.get(key)


def get_session_secret(environment: Any) -> Optional[str]:
    """Recupera la chiave di firma per i token di sessione (SESSION_SECRET con fallback su ADMIN_PASSWORD)."""
    return get_secret(environment, "SESSION_SECRET") or get_secret(environment, "ADMIN_PASSWORD")
