"""Configurazioni di base e costanti di sistema."""
import os
import re
import sys
from typing import Any, Optional

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB per immagini
MAX_VIDEO_UPLOAD_SIZE = 30 * 1024 * 1024  # 30 MB per video cantiere
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

CATEGORIE_LAVORO_VALIDE = (
    "Coperture industriali",
    "Terrazzi e lastrici",
    "Fondazioni e cantine",
    "Impermeabilizzazioni",
)

TIPI_MEDIA_LAVORO_VALIDI = ("prima", "dopo", "video")

COLONNE_LAVORO_VALIDE = {
    "titolo": 160,
    "categoria": 80,
    "descrizione": 3000,
    "localita": 160,
    "supporto": 160,
    "ciclo_sistema": 160,
    "armatura": 160,
    "applicazione": 160,
    "stratigrafia_descrizione": 3000,
}


def get_secret(environment: Any, key: str) -> Optional[str]:
    if environment is not None:
        try:
            valore = getattr(environment, key, None)
            if valore is not None:
                return str(valore).strip()
        except Exception:
            pass
    return os.environ.get(key)


def is_worker_runtime() -> bool:
    """Rileva se il backend è in esecuzione su Cloudflare Workers (Pyodide/Emscripten)."""
    return sys.platform == "emscripten" or "pyodide" in sys.modules


def maschera_email(email: str) -> str:
    """Maschera un indirizzo email per evitare PII in chiaro nei log (es. m***@dominio.it)."""
    pulita = (email or "").strip()
    if "@" not in pulita:
        return "***"
    locale, dominio = pulita.split("@", 1)
    prefisso = locale[0] if locale else "*"
    return f"{prefisso}***@{dominio}"


def get_session_secret(environment: Any) -> Optional[str]:
    """Recupera la chiave HMAC dedicata per i token di sessione.

    In produzione (Cloudflare Workers) richiede esplicitamente SESSION_SECRET dedicato
    senza accoppiarlo ad ADMIN_PASSWORD. In locale/test mantiene il fallback retroattivo.
    """
    dedicated = get_secret(environment, "SESSION_SECRET")
    if dedicated:
        return dedicated
    if is_worker_runtime():
        return None
    return get_secret(environment, "ADMIN_PASSWORD")
