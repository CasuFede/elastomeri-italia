"""Router per autenticazione Admin, Cliente e gestione sessioni."""
import secrets
import time
from datetime import datetime, timezone
from urllib.parse import quote
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response

from api.deps import verifica_credenziali
from core.config import TOKEN_SESSIONE_DURATA, get_secret, get_session_secret
from core.database import CloudflareServices, D1Store, get_environment, get_services
from core.rate_limit import (
    get_client_ip,
    is_blocked_d1,
    record_failure_d1,
    reset_failures_d1,
)
from core.security import (
    crea_hash_password,
    crea_token_reset,
    crea_token_sessione,
    is_secure_request,
    valida_complessita_password,
    valida_token_reset,
    verifica_hash_password,
)
from schemas.auth import (
    AdminLoginRequest,
    ClienteConfirmResetRequest,
    ClienteLoginRequest,
    ClienteLostPasswordRequest,
)
from services.email import invia_email_recupero_password_cliente
from services.telegram import invia_notifica_recupero_telegram

router = APIRouter(prefix="/auth", tags=["Autenticazione"])


def _store_opzionale(request: Request) -> D1Store | None:
    try:
        services = get_services(request)
        if services.database is not None:
            return D1Store(services.database)
    except Exception:
        pass
    return None


@router.get("/admin/me")
async def verifica_sessione_admin(username: str = Depends(verifica_credenziali)):
    """Endpoint leggero usato dal middleware SSR per verificare la validità crittografica del cookie admin."""
    return {"status": "ok", "username": username}


@router.post("/admin/login")
async def login_admin(
    dati: AdminLoginRequest,
    request: Request,
    response: Response,
):
    ip = get_client_ip(request)
    store = _store_opzionale(request)
    if await is_blocked_d1(store, "admin_login", ip, max_failures=5, window_seconds=300):
        raise HTTPException(
            status_code=429,
            detail="Troppi tentativi di accesso falliti. L'accesso è temporaneamente bloccato per 5 minuti.",
        )

    environment = get_environment(request)
    admin_user = get_secret(environment, "ADMIN_USERNAME")
    admin_pass = get_secret(environment, "ADMIN_PASSWORD")
    if not admin_user or not admin_pass:
        raise HTTPException(
            status_code=503,
            detail="Configurare ADMIN_USERNAME e ADMIN_PASSWORD come secrets del Worker.",
        )
    user_ok = secrets.compare_digest(
        dati.username.strip().encode("utf-8"), admin_user.encode("utf-8")
    )
    pass_ok = secrets.compare_digest(
        dati.password.encode("utf-8"), admin_pass.encode("utf-8")
    )
    if not (user_ok and pass_ok):
        await record_failure_d1(store, "admin_login", ip, window_seconds=300)
        raise HTTPException(status_code=401, detail="Nome utente o password non corretti.")

    await reset_failures_d1(store, "admin_login", ip)
    session_secret = get_session_secret(environment)
    if not session_secret:
        raise HTTPException(
            status_code=503,
            detail="Configurare SESSION_SECRET come secret del Worker.",
        )
    token = crea_token_sessione("admin", admin_user, session_secret)
    is_secure = is_secure_request(request, environment)
    response.set_cookie(
        key="poliurea_admin_session",
        value=token,
        max_age=TOKEN_SESSIONE_DURATA,
        httponly=True,
        samesite="strict",
        secure=is_secure,
        path="/",
    )
    return {"status": "success", "username": admin_user}


@router.post("/cliente/login")
async def login_cliente(
    dati: ClienteLoginRequest,
    request: Request,
    response: Response,
    services: CloudflareServices = Depends(get_services),
):
    ip = get_client_ip(request)
    store = D1Store(services.database)
    if await is_blocked_d1(store, "cliente_login", ip, max_failures=5, window_seconds=300):
        raise HTTPException(
            status_code=429,
            detail="Troppi tentativi di accesso falliti. L'accesso è temporaneamente bloccato per 5 minuti.",
        )

    email = str(dati.email).strip().lower()
    cliente = await store.one(
        "SELECT id, nome, email, password_hash, attivo, COALESCE(primo_accesso, 1) AS primo_accesso FROM clienti WHERE lower(email) = ? LIMIT 1",
        email,
    )
    if (
        not cliente
        or not cliente["attivo"]
        or not verifica_hash_password(dati.password, cliente["password_hash"])
    ):
        await record_failure_d1(store, "cliente_login", ip, window_seconds=300)
        raise HTTPException(status_code=401, detail="Email o password non corrette.")

    await reset_failures_d1(store, "cliente_login", ip)
    environment = get_environment(request)
    session_secret = get_session_secret(environment)
    if not session_secret:
        raise HTTPException(
            status_code=503,
            detail="Configurare ADMIN_PASSWORD o SESSION_SECRET come secret del Worker.",
        )
    secret_cliente = f"{session_secret}:{cliente['password_hash']}"
    token = crea_token_sessione("cliente", str(cliente["id"]), secret_cliente)

    is_secure = is_secure_request(request, environment)
    response.set_cookie(
        key="poliurea_client_session",
        value=token,
        max_age=TOKEN_SESSIONE_DURATA,
        httponly=True,
        samesite="strict",
        secure=is_secure,
        path="/",
    )
    return {
        "status": "success",
        "cliente": {
            "id": cliente["id"],
            "nome": cliente["nome"],
            "email": cliente["email"],
            "primo_accesso": bool(cliente["primo_accesso"]),
        },
    }


@router.post("/cliente/lost-password")
async def recupero_password_cliente(
    dati: ClienteLostPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    services: CloudflareServices = Depends(get_services),
):
    ip = get_client_ip(request)
    store = D1Store(services.database)
    if await is_blocked_d1(store, "lost_password", ip, max_failures=6, window_seconds=600):
        raise HTTPException(
            status_code=429,
            detail="Troppe richieste inviate. Attendi qualche minuto prima di riprovare.",
        )

    await record_failure_d1(store, "lost_password", ip, window_seconds=600)

    email = str(dati.email).strip().lower()
    messaggio_neutro = (
        f"Se l'indirizzo {email} è associato a un account registrato, riceverai a breve un'email "
        "con un link sicuro valido 30 minuti per impostare una nuova password. "
        "Controlla anche la cartella Spam."
    )

    cliente = await store.one(
        "SELECT id, nome, email, password_hash, attivo, COALESCE(ultimo_recupero_password, '') AS ultimo_recupero_password "
        "FROM clienti WHERE lower(email) = ? LIMIT 1",
        email,
    )

    # Nessuna enumerazione account e nessuna modifica di password_hash senza verifica via email
    if not cliente or not cliente.get("attivo", 1):
        return {"status": "success", "message": messaggio_neutro}

    # Limite silenzioso 1 invio ogni 24 ore per account (evita sia spam sia user enumeration via HTTP 429)
    ora_attuale = datetime.now(timezone.utc)
    ultimo_recupero_str = (cliente.get("ultimo_recupero_password") or "").strip()
    if ultimo_recupero_str:
        try:
            ultimo_recupero = datetime.fromisoformat(ultimo_recupero_str)
            if (ora_attuale - ultimo_recupero).total_seconds() < 24 * 3600:
                return {"status": "success", "message": messaggio_neutro}
        except ValueError:
            pass

    environment = get_environment(request)
    session_secret = get_session_secret(environment)
    if not session_secret:
        return {"status": "success", "message": messaggio_neutro}

    # Token HMAC monouso valido 30 minuti legato al password_hash corrente (non blocca l'account esistente)
    secret_cliente = f"{session_secret}:{cliente['password_hash']}"
    reset_token = crea_token_reset(str(cliente["id"]), secret_cliente)
    reset_url = f"https://poliureasystem.it/area-clienti?reset={quote(reset_token, safe='')}"

    await store.run(
        "UPDATE clienti SET ultimo_recupero_password = ? WHERE id = ?",
        ora_attuale.isoformat(),
        cliente["id"],
    )

    background_tasks.add_task(
        invia_email_recupero_password_cliente,
        cliente["nome"],
        cliente["email"],
        reset_url,
        environment,
    )

    token = get_secret(environment, "TELEGRAM_BOT_TOKEN")
    chat_id = get_secret(environment, "TELEGRAM_CHAT_ID")
    if token and chat_id:
        background_tasks.add_task(
            invia_notifica_recupero_telegram,
            cliente["nome"],
            cliente["email"],
            token,
            chat_id,
        )

    return {"status": "success", "message": messaggio_neutro}


@router.post("/cliente/confirm-reset")
async def conferma_reset_password_cliente(
    dati: ClienteConfirmResetRequest,
    request: Request,
    response: Response,
    services: CloudflareServices = Depends(get_services),
):
    ip = get_client_ip(request)
    store = D1Store(services.database)
    if await is_blocked_d1(store, "confirm_reset", ip, max_failures=10, window_seconds=600):
        raise HTTPException(
            status_code=429,
            detail="Troppi tentativi falliti. Riprova tra qualche minuto.",
        )

    nuova_pwd = dati.password.strip()
    errore_pwd = valida_complessita_password(nuova_pwd, lunghezza_minima=8)
    if errore_pwd:
        raise HTTPException(status_code=422, detail=errore_pwd)

    environment = get_environment(request)
    session_secret = get_session_secret(environment)
    if not session_secret:
        raise HTTPException(
            status_code=503,
            detail="Configurare ADMIN_PASSWORD o SESSION_SECRET come secret del Worker.",
        )

    parti = dati.token.strip().split(":")
    cliente = None
    if len(parti) == 5 and parti[0] == "reset":
        try:
            cliente_id = int(parti[1])
            scadenza = int(parti[2])
            if time.time() <= scadenza:
                candidato = await store.one(
                    "SELECT id, nome, email, password_hash, attivo FROM clienti WHERE id = ? LIMIT 1",
                    cliente_id,
                )
                if candidato and candidato["attivo"]:
                    secret_cliente = f"{session_secret}:{candidato['password_hash']}"
                    if valida_token_reset(dati.token.strip(), secret_cliente):
                        cliente = candidato
        except (ValueError, TypeError):
            cliente = None

    if not cliente:
        await record_failure_d1(store, "confirm_reset", ip, window_seconds=600)
        raise HTTPException(
            status_code=400,
            detail="Il link di ripristino non è valido oppure è scaduto. Richiedi un nuovo recupero password.",
        )

    await reset_failures_d1(store, "confirm_reset", ip)
    nuovo_hash = crea_hash_password(nuova_pwd)
    await store.run(
        "UPDATE clienti SET password_hash = ?, primo_accesso = 0 WHERE id = ?",
        nuovo_hash,
        cliente["id"],
    )

    secret_nuovo = f"{session_secret}:{nuovo_hash}"
    session_token = crea_token_sessione("cliente", str(cliente["id"]), secret_nuovo)
    is_secure = is_secure_request(request, environment)
    response.set_cookie(
        key="poliurea_client_session",
        value=session_token,
        max_age=TOKEN_SESSIONE_DURATA,
        httponly=True,
        samesite="strict",
        secure=is_secure,
        path="/",
    )
    return {
        "status": "success",
        "message": "Password reimpostata con successo! Accesso in corso...",
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="poliurea_admin_session", path="/")
    response.delete_cookie(key="poliurea_client_session", path="/")
    return {"status": "success", "message": "Disconnessione completata"}
