"""Router per autenticazione Admin, Cliente e gestione sessioni."""
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response

from core.config import TOKEN_SESSIONE_DURATA, get_secret, get_session_secret
from core.database import CloudflareServices, D1Store, get_environment, get_services
from core.rate_limit import get_client_ip, rate_limiter
from core.security import (
    crea_hash_password,
    crea_token_sessione,
    genera_password_casuale,
    is_secure_request,
    verifica_hash_password,
)
from schemas.auth import (
    AdminLoginRequest,
    ClienteLoginRequest,
    ClienteLostPasswordRequest,
)
from services.email import invia_email_recupero_password_cliente
from services.telegram import invia_notifica_recupero_telegram

router = APIRouter(prefix="/auth", tags=["Autenticazione"])


@router.post("/admin/login")
async def login_admin(
    dati: AdminLoginRequest,
    request: Request,
    response: Response,
):
    ip = get_client_ip(request)
    if rate_limiter.is_blocked("admin_login", ip, max_failures=5, window_seconds=300):
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
        rate_limiter.record_failure("admin_login", ip)
        raise HTTPException(status_code=401, detail="Nome utente o password non corretti.")

    rate_limiter.reset("admin_login", ip)
    session_secret = get_session_secret(environment) or admin_pass
    token = crea_token_sessione("admin", admin_user, session_secret)
    is_secure = is_secure_request(request, environment)
    response.set_cookie(
        key="poliurea_admin_session",
        value=token,
        max_age=TOKEN_SESSIONE_DURATA,
        httponly=True,
        samesite="lax",
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
    if rate_limiter.is_blocked("cliente_login", ip, max_failures=5, window_seconds=300):
        raise HTTPException(
            status_code=429,
            detail="Troppi tentativi di accesso falliti. L'accesso è temporaneamente bloccato per 5 minuti.",
        )

    email = str(dati.email).strip().lower()
    store = D1Store(services.database)
    cliente = await store.one(
        "SELECT id, nome, email, password_hash, attivo, COALESCE(primo_accesso, 1) AS primo_accesso FROM clienti WHERE lower(email) = ? LIMIT 1",
        email,
    )
    if (
        not cliente
        or not cliente["attivo"]
        or not verifica_hash_password(dati.password, cliente["password_hash"])
    ):
        rate_limiter.record_failure("cliente_login", ip)
        raise HTTPException(status_code=401, detail="Email o password non corrette.")

    rate_limiter.reset("cliente_login", ip)
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
        samesite="lax",
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
    if rate_limiter.is_blocked("lost_password", ip, max_failures=6, window_seconds=600):
        raise HTTPException(
            status_code=429,
            detail="Troppe richieste inviate. Attendi qualche minuto prima di riprovare.",
        )

    email = str(dati.email).strip().lower()
    store = D1Store(services.database)
    cliente = await store.one(
        "SELECT id, nome, email, COALESCE(ultimo_recupero_password, '') AS ultimo_recupero_password FROM clienti WHERE lower(email) = ? LIMIT 1",
        email,
    )

    if not cliente:
        rate_limiter.record_failure("lost_password", ip)
        return {
            "status": "success",
            "message": f"Se l'indirizzo {email} è associato a un account registrato, riceverai a breve un'email con la nuova password provvisoria. Controlla la casella di posta (incluso lo Spam). Al tuo accesso ti verrà richiesto di creare una password definitiva.",
        }

    # Controllo limite: consentito solo 1 volta al giorno (24 ore)
    ora_attuale = datetime.now(timezone.utc)
    ultimo_recupero_str = (cliente.get("ultimo_recupero_password") or "").strip()
    if ultimo_recupero_str:
        try:
            ultimo_recupero = datetime.fromisoformat(ultimo_recupero_str)
            differenza_secondi = (ora_attuale - ultimo_recupero).total_seconds()
            limite_secondi = 24 * 3600
            if differenza_secondi < limite_secondi:
                ore_rimaste = max(1, int((limite_secondi - differenza_secondi) // 3600))
                raise HTTPException(
                    status_code=429,
                    detail=f"Hai già effettuato una richiesta di recupero password nelle ultime 24 ore. Per motivi di sicurezza, puoi richiederla solo 1 volta al giorno. Controlla la tua casella di posta (incluso lo Spam) o riprova tra circa {ore_rimaste} ore.",
                )
        except ValueError:
            pass

    password_temporanea = genera_password_casuale(14)
    nuovo_hash = crea_hash_password(password_temporanea)
    ora_iso = ora_attuale.isoformat()

    await store.run(
        "UPDATE clienti SET password_hash = ?, primo_accesso = 1, ultimo_recupero_password = ? WHERE id = ?",
        nuovo_hash,
        ora_iso,
        cliente["id"],
    )

    environment = get_environment(request)
    background_tasks.add_task(
        invia_email_recupero_password_cliente,
        cliente["nome"],
        cliente["email"],
        password_temporanea,
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

    return {
        "status": "success",
        "message": f"Se l'indirizzo {email} è associato a un account registrato, riceverai a breve un'email con la nuova password provvisoria. Controlla la casella di posta (incluso lo Spam). Al tuo accesso ti verrà richiesto di creare una password definitiva.",
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="poliurea_admin_session", path="/")
    response.delete_cookie(key="poliurea_client_session", path="/")
    return {"status": "success", "message": "Disconnessione completata"}
