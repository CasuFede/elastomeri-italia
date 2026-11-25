"""Dipendenze di autenticazione e contesto per FastAPI."""
import secrets
import time
from typing import Any, Optional
from fastapi import Depends, HTTPException, Request

from core.config import get_secret, get_session_secret
from core.database import CloudflareServices, D1Store, get_environment, get_services
from core.security import valida_token_sessione


def verifica_credenziali(request: Request) -> str:
    environment = get_environment(request)
    admin_user = get_secret(environment, "ADMIN_USERNAME")
    admin_pass = get_secret(environment, "ADMIN_PASSWORD")
    if not admin_user or not admin_pass:
        raise HTTPException(
            status_code=503,
            detail="Configurare ADMIN_USERNAME e ADMIN_PASSWORD come secrets del Worker.",
        )
    session_secret = get_session_secret(environment) or admin_pass

    # 1. Verifica tramite Cookie HttpOnly (browser)
    cookie_token = request.cookies.get("poliurea_admin_session")
    if cookie_token:
        username = valida_token_sessione(cookie_token, session_secret, "admin")
        if username and secrets.compare_digest(
            username.encode("utf-8"), admin_user.encode("utf-8")
        ):
            return username

    # 2. Verifica tramite Bearer token firmato HMAC nell'header Authorization
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        bearer_token = auth_header[7:].strip()
        username = valida_token_sessione(bearer_token, session_secret, "admin")
        if username and secrets.compare_digest(
            username.encode("utf-8"), admin_user.encode("utf-8")
        ):
            return username

    raise HTTPException(
        status_code=401,
        detail="Autenticazione richiesta",
    )


async def _valida_token_cliente(
    token: str, store: D1Store, session_secret: str
) -> Optional[dict[str, Any]]:
    """Valida un token di sessione cliente controllando prima la scadenza per evitare query D1 inutili."""
    try:
        parti = token.split(":")
        if len(parti) != 5 or parti[0] != "cliente":
            return None
        cliente_id = int(parti[1])
        scadenza = int(parti[2])

        # Controllo scadenza anticipato: evita accessi a D1 se il token è scaduto
        if time.time() > scadenza:
            return None

        cliente = await store.one(
            "SELECT id, nome, email, password_hash, attivo, data_creazione, COALESCE(primo_accesso, 1) AS primo_accesso "
            "FROM clienti WHERE id = ? LIMIT 1",
            cliente_id,
        )
        if cliente and cliente["attivo"]:
            secret_cliente = f"{session_secret}:{cliente['password_hash']}"
            if valida_token_sessione(token, secret_cliente, "cliente"):
                return cliente
    except (ValueError, TypeError):
        pass
    return None


async def verifica_cliente(
    request: Request,
    services: CloudflareServices = Depends(get_services),
) -> dict[str, Any]:
    store = D1Store(services.database)
    environment = get_environment(request)
    session_secret = get_session_secret(environment)
    if not session_secret:
        raise HTTPException(
            status_code=503,
            detail="Configurare ADMIN_PASSWORD o SESSION_SECRET come secret del Worker.",
        )

    # 1. Verifica tramite Cookie HttpOnly (browser)
    cookie_token = request.cookies.get("poliurea_client_session")
    if cookie_token:
        cliente = await _valida_token_cliente(cookie_token, store, session_secret)
        if cliente:
            return cliente

    # 2. Verifica tramite Bearer token firmato HMAC
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        bearer_token = auth_header[7:].strip()
        cliente = await _valida_token_cliente(bearer_token, store, session_secret)
        if cliente:
            return cliente

    raise HTTPException(
        status_code=401,
        detail="Credenziali cliente non valide",
    )
