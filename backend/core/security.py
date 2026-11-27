"""Funzioni crittografiche, hashing password e gestione token di sessione HMAC."""
import hashlib
import hmac
import os
import secrets
import time
from typing import Any, Optional

from core.config import PASSWORD_ITERATIONS, TOKEN_SESSIONE_DURATA, get_secret


def pbkdf2_sha256_bytes(password: bytes, salt: bytes, iterations: int) -> bytes:
    if hasattr(hashlib, "pbkdf2_hmac"):
        try:
            return hashlib.pbkdf2_hmac("sha256", password, salt, iterations)
        except (AttributeError, ValueError):
            pass
    # Fallback PBKDF2 HMAC-SHA256 (1 blocco da 32 byte) per ambienti Pyodide senza OpenSSL
    u = hmac.new(password, salt + b"\x00\x00\x00\x01", hashlib.sha256).digest()
    result = bytearray(u)
    for _ in range(iterations - 1):
        u = hmac.new(password, u, hashlib.sha256).digest()
        for i in range(32):
            result[i] ^= u[i]
    return bytes(result)


def valida_complessita_password(password: str, lunghezza_minima: int = 8) -> Optional[str]:
    """Verifica i requisiti minimi di sicurezza password; restituisce il messaggio di errore o None."""
    pulita = (password or "").strip()
    if (
        len(pulita) < lunghezza_minima
        or not any(c.isupper() for c in pulita)
        or not any(c.islower() for c in pulita)
        or not any(c.isdigit() for c in pulita)
    ):
        return (
            f"La password deve contenere almeno {lunghezza_minima} caratteri, "
            "una lettera maiuscola, una minuscola e un numero."
        )
    return None


def crea_hash_password(password: str) -> str:
    sale = secrets.token_bytes(16)
    digest = pbkdf2_sha256_bytes(
        password.encode("utf8"), sale, PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${sale.hex()}${digest.hex()}"


def genera_password_casuale(lunghezza: int = 14) -> str:
    maiuscole = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    minuscole = "abcdefghijkmnopqrstuvwxyz"
    cifre = "23456789"
    simboli = "!@#$%*-_"
    tutti = maiuscole + minuscole + cifre + simboli

    pwd = [
        secrets.choice(maiuscole),
        secrets.choice(minuscole),
        secrets.choice(cifre),
        secrets.choice(simboli),
    ]
    for _ in range(max(0, lunghezza - 4)):
        pwd.append(secrets.choice(tutti))
    secrets.SystemRandom().shuffle(pwd)
    return "".join(pwd)


def verifica_hash_password(password: str, password_hash: str) -> bool:
    try:
        algoritmo, iterazioni_str, sale_hex, digest_atteso = password_hash.split("$", 3)
        if algoritmo != "pbkdf2_sha256":
            return False
        iterazioni = int(iterazioni_str)
        # Rifiuta hash con iterazioni fuori scala per prevenire DoS crittografici
        if iterazioni > 600_000 or iterazioni < 10_000:
            return False
        digest_calcolato = pbkdf2_sha256_bytes(
            password.encode("utf8"),
            bytes.fromhex(sale_hex),
            iterazioni,
        ).hex()
        return secrets.compare_digest(digest_calcolato, digest_atteso)
    except (ValueError, TypeError):
        return False


TOKEN_RESET_DURATA = 1800  # 30 minuti


def crea_token_sessione(
    tipo: str, identificatore: str, secret: str, durata_secondi: int = TOKEN_SESSIONE_DURATA
) -> str:
    scadenza = int(time.time()) + durata_secondi
    nonce = secrets.token_hex(12)
    messaggio = f"{tipo}:{identificatore}:{scadenza}:{nonce}"
    firma = hmac.new(
        secret.encode("utf-8"), messaggio.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"{messaggio}:{firma}"


def crea_token_reset(identificatore: str, secret: str) -> str:
    """Crea un token monouso di reset password valido 30 minuti (legato al password_hash corrente)."""
    return crea_token_sessione("reset", identificatore, secret, durata_secondi=TOKEN_RESET_DURATA)


def valida_token_reset(token: str, secret: str) -> Optional[str]:
    """Valida un token monouso di reset password."""
    return valida_token_sessione(token, secret, "reset")


def valida_token_sessione(
    token: str, secret: str, tipo_atteso: str
) -> Optional[str]:
    try:
        parti = token.split(":")
        if len(parti) != 5:
            return None
        tipo, identificatore, scadenza_str, nonce, firma = parti
        if tipo != tipo_atteso:
            return None
        if time.time() > int(scadenza_str):
            return None
        messaggio = f"{tipo}:{identificatore}:{scadenza_str}:{nonce}"
        firma_attesa = hmac.new(
            secret.encode("utf-8"), messaggio.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not secrets.compare_digest(firma, firma_attesa):
            return None
        return identificatore
    except Exception:
        return None


def is_secure_request(request: Any, environment: Any = None) -> bool:
    cookie_secure_env = os.environ.get("COOKIE_SECURE", "")
    if environment:
        cookie_secure_env = get_secret(environment, "COOKIE_SECURE") or cookie_secure_env
    if cookie_secure_env.lower() in ("true", "1", "yes"):
        return True
    if cookie_secure_env.lower() in ("false", "0", "no"):
        return False

    if getattr(request, "url", None) and request.url.scheme == "https":
        return True
    if request.headers.get("x-forwarded-proto", "").lower() == "https":
        return True
    if request.headers.get("x-forwarded-ssl", "").lower() == "on":
        return True
    cf_visitor = request.headers.get("cf-visitor")
    if cf_visitor and '"scheme":"https"' in cf_visitor.replace(" ", ""):
        return True
    return False
