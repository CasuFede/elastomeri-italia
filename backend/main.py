import hashlib
import hmac
import html
import json
import os
import re
import secrets
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from chat_knowledge import rispondi

app = FastAPI(title="API Poliurea System")

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
MAX_UPLOAD_COUNT = 5
STATI_PREVENTIVO = {
    "ricevuto": "Ricevuto",
    "in_valutazione": "In valutazione",
    "preventivo_inviato": "Preventivo inviato",
    "in_lavorazione": "In lavorazione",
    "completato": "Completato",
    "annullato": "Annullato",
}
PASSWORD_ITERATIONS = 310_000
TELEFONO_REGEX = re.compile(r"^\+?[0-9\s\-\.\(\)]{6,25}$")


class InMemoryRateLimiter:
    def __init__(self):
        self._hits: dict[str, list[float]] = defaultdict(list)

    def prune_if_needed(self):
        if len(self._hits) > 2000:
            now = time.time()
            keys_to_delete = [
                k for k, v in self._hits.items()
                if not v or now - v[-1] > 3600
            ]
            for k in keys_to_delete:
                del self._hits[k]

    def check(self, bucket: str, ip: str, max_requests: int, window_seconds: int) -> bool:
        self.prune_if_needed()
        now = time.time()
        key = f"{bucket}:{ip}"
        cutoff = now - window_seconds
        timestamps = [t for t in self._hits[key] if t > cutoff]
        if len(timestamps) >= max_requests:
            self._hits[key] = timestamps
            return False
        timestamps.append(now)
        self._hits[key] = timestamps
        return True

    def record_failure(self, bucket: str, ip: str):
        self.prune_if_needed()
        now = time.time()
        key = f"{bucket}:{ip}"
        self._hits[key].append(now)

    def is_blocked(self, bucket: str, ip: str, max_failures: int, window_seconds: int) -> bool:
        now = time.time()
        key = f"{bucket}:{ip}"
        cutoff = now - window_seconds
        failures = [t for t in self._hits[key] if t > cutoff]
        self._hits[key] = failures
        return len(failures) >= max_failures

    def reset(self, bucket: str, ip: str):
        key = f"{bucket}:{ip}"
        self._hits.pop(key, None)


rate_limiter = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    x_forwarded = request.headers.get("x-forwarded-for")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    x_real = request.headers.get("x-real-ip")
    if x_real:
        return x_real.strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


@dataclass
class CloudflareServices:
    database: Any
    uploads: Any


class D1Store:
    def __init__(self, binding: Any):
        self.binding = binding

    async def all(self, query: str, *parameters: Any) -> list[dict[str, Any]]:
        statement = self.binding.prepare(query)
        if parameters:
            statement = statement.bind(*parameters)
        result = await statement.all()
        return list(result.results)

    async def one(self, query: str, *parameters: Any) -> Optional[dict[str, Any]]:
        rows = await self.all(query, *parameters)
        return rows[0] if rows else None

    async def run(self, query: str, *parameters: Any) -> Any:
        statement = self.binding.prepare(query)
        if parameters:
            statement = statement.bind(*parameters)
        return await statement.run()


def get_environment(request: Request) -> Any:
    environment = request.scope.get("env")
    if environment is None:
        raise HTTPException(
            status_code=503,
            detail="Binding Cloudflare non disponibile per questa richiesta.",
        )
    return environment


def get_services(request: Request) -> CloudflareServices:
    environment = get_environment(request)
    try:
        return CloudflareServices(
            database=environment.DB,
            uploads=environment.UPLOADS,
        )
    except AttributeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Configurare i binding D1 (DB) e R2 (UPLOADS) del Worker.",
        ) from exc


@app.middleware("http")
async def remove_api_prefix(request: Request, call_next: Any) -> Response:
    path = request.scope["path"]
    if path == "/api":
        request.scope["path"] = "/"
        request.scope["raw_path"] = b"/"
    elif path.startswith("/api/"):
        api_path = path[4:]
        request.scope["path"] = api_path
        request.scope["raw_path"] = api_path.encode("utf-8")
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


class PreventivoRequest(BaseModel):
    nome: str
    email: EmailStr
    telefono: str
    servizio: str
    messaggio: Optional[str] = None


class LavoroAggiornamento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titolo: Optional[str] = Field(default=None, max_length=160)
    descrizione: Optional[str] = Field(default=None, max_length=3000)
    localita: Optional[str] = Field(default=None, max_length=160)


class ClienteCreazione(BaseModel):
    nome: str
    email: EmailStr
    password: str


class StatoPreventivoAggiornamento(BaseModel):
    stato: str
    note_cliente: Optional[str] = ""


class ChatMessage(BaseModel):
    role: Literal["user", "model"]
    content: str = Field(min_length=1, max_length=1200)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=12)


@app.post("/chat")
async def chat_informativa(dati: ChatRequest, request: Request):
    ip = get_client_ip(request)
    if not rate_limiter.check("chat", ip, max_requests=30, window_seconds=60):
        raise HTTPException(
            status_code=429,
            detail="Stai inviando troppi messaggi in poco tempo. Attendi qualche istante prima di continuare.",
        )
    messaggi = dati.messages
    if (
        messaggi[0].role != "user"
        or messaggi[-1].role != "user"
        or any(not messaggio.content.strip() for messaggio in messaggi)
        or any(
            precedente.role == corrente.role
            for precedente, corrente in zip(messaggi, messaggi[1:])
        )
    ):
        raise HTTPException(
            status_code=422,
            detail="La conversazione non è valida. Ricarica la pagina e riprova.",
        )

    contesto = next(
        (
            messaggio.content.strip()
            for messaggio in reversed(messaggi[:-1])
            if messaggio.role == "user"
        ),
        "",
    )
    return {
        "answer": rispondi(
            messaggi[-1].content.strip(),
            contesto=contesto,
        )
    }


async def invia_notifica_telegram(
    dati: PreventivoRequest,
    token: Optional[str],
    chat_id: Optional[str],
) -> None:
    if not token or not chat_id:
        print("Credenziali Telegram mancanti nei secrets del Worker.")
        return

    testo_messaggio = (
        f"🚀 <b>Nuovo Preventivo Poliurea System!</b>\n\n"
        f"👤 <b>Nome:</b> {html.escape(dati.nome)}\n"
        f"📧 <b>Email:</b> {html.escape(str(dati.email))}\n"
        f"📞 <b>Telefono:</b> {html.escape(dati.telefono)}\n"
        f"🛠 <b>Servizio:</b> {html.escape(dati.servizio)}\n"
        f"💬 <b>Messaggio:</b>\n{html.escape(dati.messaggio or 'Nessun messaggio specificato')}"
    )
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
        from js import fetch

        response = await fetch(
            url,
            {
                "method": "POST",
                "headers": {"content-type": "application/json"},
                "body": json.dumps(payload),
            },
        )
        if not response.ok:
            print(f"Errore durante l'invio a Telegram: HTTP {response.status}")
    except Exception as exc:
        print(f"Errore durante l'invio a Telegram: {exc}")


def tipo_immagine(contenuto: bytes) -> Optional[tuple[str, str]]:
    if contenuto.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if contenuto.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if len(contenuto) >= 12 and contenuto[:4] == b"RIFF" and contenuto[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


async def salva_su_r2(bucket: Any, key: str, contenuto: bytes) -> None:
    await bucket.put(key, contenuto)


async def elimina_da_r2(bucket: Any, key: str) -> None:
    await bucket.delete(key)


async def leggi_da_r2(bucket: Any, key: str) -> Optional[bytes]:
    oggetto = await bucket.get(key)
    if oggetto is None:
        return None
    from js import Uint8Array

    contenuto = await oggetto.arrayBuffer()
    return bytes(Uint8Array.new(contenuto).to_py())


async def risposta_file(bucket: Any, key: str, tipo_mime: str) -> Response:
    contenuto = await leggi_da_r2(bucket, key)
    if contenuto is None:
        raise HTTPException(status_code=404, detail="File non disponibile.")
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": (
            "public, max-age=86400, immutable"
            if key.startswith("lavori/")
            else "private, no-cache"
        ),
    }
    return Response(content=contenuto, media_type=tipo_mime, headers=headers)


def valore_data_iso(valore: Any) -> Optional[str]:
    if valore is None:
        return None
    if isinstance(valore, datetime):
        return valore.isoformat()
    return str(valore).replace(" ", "T", 1)


def get_secret(environment: Any, name: str) -> Optional[str]:
    try:
        return getattr(environment, name)
    except AttributeError:
        return None


security = HTTPBasic(auto_error=False)
TOKEN_SESSIONE_DURATA = 8 * 3600  # 8 ore


def crea_token_sessione(tipo: str, identificatore: str, secret: str) -> str:
    scadenza = int(time.time()) + TOKEN_SESSIONE_DURATA
    nonce = secrets.token_hex(8)
    messaggio = f"{tipo}:{identificatore}:{scadenza}:{nonce}"
    firma = hmac.new(
        secret.encode("utf-8"), messaggio.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"{messaggio}:{firma}"


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


def verifica_credenziali(
    request: Request,
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
) -> str:
    environment = get_environment(request)
    admin_user = get_secret(environment, "ADMIN_USERNAME")
    admin_pass = get_secret(environment, "ADMIN_PASSWORD")
    if not admin_user or not admin_pass:
        raise HTTPException(
            status_code=503,
            detail="Configurare ADMIN_USERNAME e ADMIN_PASSWORD come secrets del Worker.",
        )

    # 1. Verifica tramite Cookie HttpOnly (browser)
    cookie_token = request.cookies.get("poliurea_admin_session")
    if cookie_token:
        username = valida_token_sessione(cookie_token, admin_pass, "admin")
        if username and secrets.compare_digest(
            username.encode("utf-8"), admin_user.encode("utf-8")
        ):
            return username

    # 2. Verifica tramite Bearer token nell'header Authorization
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        bearer_token = auth_header[7:].strip()
        username = valida_token_sessione(bearer_token, admin_pass, "admin")
        if username and secrets.compare_digest(
            username.encode("utf-8"), admin_user.encode("utf-8")
        ):
            return username

    # 3. Fallback: HTTP Basic Auth (per CLI, cURL o script)
    if credentials:
        username_corretta = secrets.compare_digest(
            credentials.username.encode("utf8"), admin_user.encode("utf8")
        )
        password_corretta = secrets.compare_digest(
            credentials.password.encode("utf8"), admin_pass.encode("utf8")
        )
        if username_corretta and password_corretta:
            return credentials.username

    raise HTTPException(
        status_code=401,
        detail="Autenticazione richiesta",
        headers={"WWW-Authenticate": "Basic"},
    )


def crea_hash_password(password: str) -> str:
    sale = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf8"), sale, PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${sale.hex()}${digest.hex()}"


def verifica_hash_password(password: str, password_hash: str) -> bool:
    try:
        algoritmo, iterazioni, sale_hex, digest_atteso = password_hash.split("$", 3)
        if algoritmo != "pbkdf2_sha256":
            return False
        digest_calcolato = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf8"),
            bytes.fromhex(sale_hex),
            int(iterazioni),
        ).hex()
        return secrets.compare_digest(digest_calcolato, digest_atteso)
    except (ValueError, TypeError):
        return False


async def verifica_cliente(
    request: Request,
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
    services: CloudflareServices = Depends(get_services),
) -> dict[str, Any]:
    store = D1Store(services.database)
    environment = get_environment(request)
    admin_pass = get_secret(environment, "ADMIN_PASSWORD") or "secret_fallback"

    # 1. Verifica tramite Cookie HttpOnly (browser)
    cookie_token = request.cookies.get("poliurea_client_session")
    if cookie_token:
        try:
            parti = cookie_token.split(":")
            if len(parti) == 5 and parti[0] == "cliente":
                cliente_id = int(parti[1])
                cliente = await store.one(
                    "SELECT id, nome, email, password_hash, attivo, data_creazione "
                    "FROM clienti WHERE id = ? LIMIT 1",
                    cliente_id,
                )
                if cliente and cliente["attivo"]:
                    secret_cliente = f"{admin_pass}:{cliente['password_hash']}"
                    if valida_token_sessione(cookie_token, secret_cliente, "cliente"):
                        return cliente
        except (ValueError, TypeError):
            pass

    # 2. Verifica tramite Bearer token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        bearer_token = auth_header[7:].strip()
        try:
            parti = bearer_token.split(":")
            if len(parti) == 5 and parti[0] == "cliente":
                cliente_id = int(parti[1])
                cliente = await store.one(
                    "SELECT id, nome, email, password_hash, attivo, data_creazione "
                    "FROM clienti WHERE id = ? LIMIT 1",
                    cliente_id,
                )
                if cliente and cliente["attivo"]:
                    secret_cliente = f"{admin_pass}:{cliente['password_hash']}"
                    if valida_token_sessione(bearer_token, secret_cliente, "cliente"):
                        return cliente
        except (ValueError, TypeError):
            pass

    # 3. Fallback: HTTP Basic Auth
    if credentials:
        email = credentials.username.strip().lower()
        cliente = await store.one(
            "SELECT id, nome, email, password_hash, attivo, data_creazione "
            "FROM clienti WHERE lower(email) = ? LIMIT 1",
            email,
        )
        if (
            cliente
            and cliente["attivo"]
            and verifica_hash_password(credentials.password, cliente["password_hash"])
        ):
            return cliente

    raise HTTPException(
        status_code=401,
        detail="Credenziali cliente non valide",
        headers={"WWW-Authenticate": "Basic"},
    )


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class ClienteLoginRequest(BaseModel):
    email: EmailStr
    password: str


@app.post("/auth/admin/login")
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
    token = crea_token_sessione("admin", admin_user, admin_pass)
    is_secure = (
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto") == "https"
    )
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


@app.post("/auth/cliente/login")
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
        "SELECT id, nome, email, password_hash, attivo FROM clienti WHERE lower(email) = ? LIMIT 1",
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
    admin_pass = get_secret(environment, "ADMIN_PASSWORD") or "secret_fallback"
    secret_cliente = f"{admin_pass}:{cliente['password_hash']}"
    token = crea_token_sessione("cliente", str(cliente["id"]), secret_cliente)

    is_secure = (
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto") == "https"
    )
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
        },
    }


@app.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key="poliurea_admin_session", path="/")
    response.delete_cookie(key="poliurea_client_session", path="/")
    return {"status": "success", "message": "Disconnessione completata"}


@app.post("/preventivo")
async def richiedi_preventivo(
    request: Request,
    background_tasks: BackgroundTasks,
    nome: str = Form(...),
    email: EmailStr = Form(...),
    telefono: str = Form(...),
    comune: str = Form(...),
    tipo_immobile: str = Form(...),
    area_intervento: str = Form(...),
    situazione: str = Form(...),
    metratura: str = Form(...),
    messaggio: Optional[str] = Form(default=None),
    consenso: bool = Form(...),
    files: Optional[list[UploadFile]] = File(default=None),
    services: CloudflareServices = Depends(get_services),
):
    ip = get_client_ip(request)
    if not rate_limiter.check("preventivo", ip, max_requests=5, window_seconds=600):
        raise HTTPException(
            status_code=429,
            detail="Hai inviato troppe richieste in poco tempo. Attendi qualche minuto prima di riprovare.",
        )

    scelte = {
        "tipo_immobile": (tipo_immobile, {"Condominio", "Casa indipendente", "Capannone industriale"}),
        "area_intervento": (area_intervento, {"Terrazzi / Balconi", "Tetti / Sottotetto", "Fondazioni / Cantine", "Altro"}),
        "situazione": (situazione, {"Infiltrazione attiva (emergenza)", "Manutenzione preventiva", "Nuova costruzione"}),
        "metratura": (metratura, {"< 50 mq", "50–150 mq", "> 150 mq"}),
    }
    for campo, (valore, opzioni) in scelte.items():
        if valore not in opzioni:
            raise HTTPException(status_code=422, detail=f"Valore non valido per {campo}")
    if not consenso:
        raise HTTPException(
            status_code=400,
            detail="È necessario accettare il trattamento dei dati per inviare la richiesta.",
        )

    nome = nome.strip()
    telefono = telefono.strip()
    comune = comune.strip()
    messaggio = (messaggio or "").strip()

    if not (2 <= len(nome) <= 120):
        raise HTTPException(
            status_code=422,
            detail="Il nome deve contenere tra 2 e 120 caratteri.",
        )

    if not TELEFONO_REGEX.match(telefono):
        raise HTTPException(
            status_code=422,
            detail="Numero di telefono non valido. Inserisci un recapito telefonico corretto.",
        )

    if not (2 <= len(comune) <= 100):
        raise HTTPException(
            status_code=422,
            detail="Il comune deve contenere tra 2 e 100 caratteri.",
        )

    if len(messaggio) > 2000:
        raise HTTPException(
            status_code=422,
            detail="Il messaggio non può superare i 2000 caratteri.",
        )

    allegati_preparati = []
    totale_byte = 0
    for file in files or []:
        contenuto = await file.read(MAX_UPLOAD_SIZE - totale_byte + 1)
        if not contenuto:
            continue
        if totale_byte + len(contenuto) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="Le foto superano il limite totale di 10 MB.")
        totale_byte += len(contenuto)
        tipo = tipo_immagine(contenuto)
        if not tipo:
            raise HTTPException(status_code=415, detail="Sono consentite solo immagini JPG, PNG o WEBP.")
        nome_originale = os.path.basename((file.filename or "foto").replace("\\", "/"))[:255]
        allegati_preparati.append((contenuto, nome_originale, tipo))
        if len(allegati_preparati) > MAX_UPLOAD_COUNT:
            raise HTTPException(
                status_code=413,
                detail=f"Puoi allegare al massimo {MAX_UPLOAD_COUNT} foto.",
            )

    servizio = f"{area_intervento} · {tipo_immobile}"
    dettagli = [
        f"Situazione: {situazione}",
        f"Metratura: {metratura}",
        f"Comune dell'intervento: {comune}",
    ]
    if messaggio:
        dettagli.extend(["", f"Note: {messaggio}"])
    dati = PreventivoRequest(
        nome=nome,
        email=email,
        telefono=telefono,
        servizio=servizio,
        messaggio="\n".join(dettagli),
    )

    store = D1Store(services.database)
    chiavi_caricate = []
    id_preventivo = None
    try:
        for contenuto, nome_originale, (tipo_mime, estensione) in allegati_preparati:
            nome_file = f"{uuid.uuid4().hex}{estensione}"
            chiave = f"allegati/{nome_file}"
            await salva_su_r2(services.uploads, chiave, contenuto)
            chiavi_caricate.append(chiave)

        preventivo = await store.one(
            "INSERT INTO preventivi "
            "(nome, email, telefono, servizio, messaggio, stato, note_cliente, data_richiesta) "
            "VALUES (?, ?, ?, ?, ?, 'ricevuto', '', ?) RETURNING id",
            dati.nome,
            str(dati.email),
            dati.telefono,
            dati.servizio,
            dati.messaggio,
            datetime.now(timezone.utc).isoformat(),
        )
        if preventivo is None:
            raise RuntimeError("D1 non ha restituito l'identificativo del preventivo creato.")
        id_preventivo = preventivo["id"]

        for chiave, (_, nome_originale, (tipo_mime, _)) in zip(
            chiavi_caricate, allegati_preparati
        ):
            nome_file = chiave.removeprefix("allegati/")
            await store.run(
                "INSERT INTO allegati (preventivo_id, nome_file, nome_originale, tipo_mime) "
                "VALUES (?, ?, ?, ?)",
                preventivo["id"],
                nome_file,
                nome_originale,
                tipo_mime,
            )
    except Exception:
        if id_preventivo is not None:
            await store.run(
                "DELETE FROM allegati WHERE preventivo_id = ?", id_preventivo
            )
            await store.run("DELETE FROM preventivi WHERE id = ?", id_preventivo)
        for chiave in chiavi_caricate:
            await elimina_da_r2(services.uploads, chiave)
        raise

    environment = get_environment(request)
    background_tasks.add_task(
        invia_notifica_telegram,
        dati,
        get_secret(environment, "TELEGRAM_BOT_TOKEN"),
        get_secret(environment, "TELEGRAM_CHAT_ID"),
    )
    return {
        "status": "success",
        "message": "Richiesta ricevuta",
        "id_pratica": preventivo["id"],
    }


@app.get("/preventivi")
async def leggi_preventivi(
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    store = D1Store(services.database)
    preventivi = await store.all(
        "SELECT id, nome, email, telefono, servizio, messaggio, stato, note_cliente, data_richiesta "
        "FROM preventivi ORDER BY data_richiesta DESC"
    )
    allegati = await store.all(
        "SELECT id, preventivo_id, nome_originale FROM allegati ORDER BY id"
    )
    allegati_per_preventivo: dict[int, list[dict[str, Any]]] = {}
    for allegato in allegati:
        allegati_per_preventivo.setdefault(allegato["preventivo_id"], []).append(
            {"id": allegato["id"], "nome": allegato["nome_originale"]}
        )
    dati = [
        {
            "id": preventivo["id"],
            "nome": preventivo["nome"],
            "email": preventivo["email"],
            "telefono": preventivo["telefono"],
            "servizio": preventivo["servizio"],
            "messaggio": preventivo["messaggio"],
            "stato": preventivo["stato"],
            "note_cliente": preventivo["note_cliente"],
            "data_richiesta": valore_data_iso(preventivo["data_richiesta"]),
            "allegati": allegati_per_preventivo.get(preventivo["id"], []),
        }
        for preventivo in preventivi
    ]
    return {
        "status": "success",
        "autenticato_come": username,
        "totale_richieste": len(dati),
        "dati": dati,
    }


@app.get("/clienti")
async def leggi_clienti(
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    clienti = await D1Store(services.database).all(
        "SELECT id, nome, email, attivo, data_creazione FROM clienti "
        "ORDER BY data_creazione DESC"
    )
    preventivi_per_email = await D1Store(services.database).all(
        "SELECT lower(email) AS email, COUNT(*) AS totale FROM preventivi "
        "GROUP BY lower(email)"
    )
    conteggi = {riga["email"]: riga["totale"] for riga in preventivi_per_email}
    return {
        "dati": [
            {
                "id": cliente["id"],
                "nome": cliente["nome"],
                "email": cliente["email"],
                "attivo": bool(cliente["attivo"]),
                "preventivi": conteggi.get(cliente["email"].lower(), 0),
            }
            for cliente in clienti
        ]
    }


@app.post("/clienti", status_code=201)
async def crea_cliente(
    dati: ClienteCreazione,
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    nome = dati.nome.strip()
    email = str(dati.email).strip().lower()
    if not nome or len(nome) > 160:
        raise HTTPException(
            status_code=422,
            detail="Il nome è obbligatorio e non può superare 160 caratteri.",
        )
    if len(dati.password) < 12:
        raise HTTPException(
            status_code=422,
            detail="La password iniziale deve contenere almeno 12 caratteri.",
        )
    store = D1Store(services.database)
    if await store.one("SELECT id FROM clienti WHERE lower(email) = ? LIMIT 1", email):
        raise HTTPException(status_code=409, detail="Esiste già un account per questa email.")

    cliente = await store.one(
        "INSERT INTO clienti (nome, email, password_hash, attivo, data_creazione) "
        "VALUES (?, ?, ?, 1, ?) RETURNING id",
        nome,
        email,
        crea_hash_password(dati.password),
        datetime.now(timezone.utc).isoformat(),
    )
    if cliente is None:
        raise RuntimeError("D1 non ha restituito l'identificativo del cliente creato.")
    return {"id": cliente["id"], "nome": nome, "email": email, "attivo": True}


@app.patch("/preventivi/{preventivo_id}/stato")
async def aggiorna_stato_preventivo(
    preventivo_id: int,
    modifiche: StatoPreventivoAggiornamento,
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    if modifiche.stato not in STATI_PREVENTIVO:
        raise HTTPException(status_code=422, detail="Stato del preventivo non valido.")
    note_cliente = (modifiche.note_cliente or "").strip()
    if len(note_cliente) > 1200:
        raise HTTPException(
            status_code=422,
            detail="Le indicazioni al cliente non possono superare 1200 caratteri.",
        )
    store = D1Store(services.database)
    preventivo = await store.one(
        "SELECT id FROM preventivi WHERE id = ? LIMIT 1", preventivo_id
    )
    if not preventivo:
        raise HTTPException(status_code=404, detail="Preventivo non trovato.")
    await store.run(
        "UPDATE preventivi SET stato = ?, note_cliente = ? WHERE id = ?",
        modifiche.stato,
        note_cliente,
        preventivo_id,
    )
    return {
        "id": preventivo_id,
        "stato": modifiche.stato,
        "note_cliente": note_cliente,
    }


@app.get("/area-clienti")
async def leggi_area_cliente(
    cliente: dict[str, Any] = Depends(verifica_cliente),
    services: CloudflareServices = Depends(get_services),
):
    store = D1Store(services.database)
    preventivi = await store.all(
        "SELECT id, servizio, messaggio, stato, note_cliente, data_richiesta "
        "FROM preventivi WHERE lower(email) = ? ORDER BY data_richiesta DESC",
        cliente["email"].lower(),
    )
    allegati = await store.all(
        "SELECT a.id, a.preventivo_id, a.nome_originale "
        "FROM allegati a "
        "INNER JOIN preventivi p ON a.preventivo_id = p.id "
        "WHERE lower(p.email) = ? ORDER BY a.id",
        cliente["email"].lower(),
    )
    allegati_per_preventivo: dict[int, list[dict[str, Any]]] = {}
    for allegato in allegati:
        allegati_per_preventivo.setdefault(allegato["preventivo_id"], []).append(
            {"id": allegato["id"], "nome": allegato["nome_originale"]}
        )
    return {
        "cliente": {"nome": cliente["nome"], "email": cliente["email"]},
        "dati": [
            {
                "id": preventivo["id"],
                "servizio": preventivo["servizio"],
                "messaggio": preventivo["messaggio"] or "",
                "stato": preventivo["stato"],
                "stato_label": STATI_PREVENTIVO.get(
                    preventivo["stato"], STATI_PREVENTIVO["ricevuto"]
                ),
                "note_cliente": preventivo["note_cliente"] or "",
                "data_richiesta": valore_data_iso(preventivo["data_richiesta"]),
                "allegati": allegati_per_preventivo.get(preventivo["id"], []),
            }
            for preventivo in preventivi
        ],
    }


@app.get("/area-clienti/preventivi/{preventivo_id}/allegati/{allegato_id}")
async def leggi_allegato_cliente(
    preventivo_id: int,
    allegato_id: int,
    cliente: dict[str, Any] = Depends(verifica_cliente),
    services: CloudflareServices = Depends(get_services),
):
    store = D1Store(services.database)
    preventivo = await store.one(
        "SELECT id FROM preventivi WHERE id = ? AND lower(email) = ? LIMIT 1",
        preventivo_id,
        cliente["email"].lower(),
    )
    if not preventivo:
        raise HTTPException(status_code=404, detail="Preventivo non trovato.")
    allegato = await store.one(
        "SELECT nome_file, tipo_mime FROM allegati "
        "WHERE id = ? AND preventivo_id = ? LIMIT 1",
        allegato_id,
        preventivo_id,
    )
    if not allegato:
        raise HTTPException(status_code=404, detail="Allegato non trovato.")
    return await risposta_file(
        services.uploads,
        f"allegati/{allegato['nome_file']}",
        allegato["tipo_mime"],
    )


@app.get("/preventivi/{preventivo_id}/allegati/{allegato_id}")
async def leggi_allegato(
    preventivo_id: int,
    allegato_id: int,
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    allegato = await D1Store(services.database).one(
        "SELECT nome_file, tipo_mime FROM allegati "
        "WHERE id = ? AND preventivo_id = ? LIMIT 1",
        allegato_id,
        preventivo_id,
    )
    if not allegato:
        raise HTTPException(status_code=404, detail="Allegato non trovato")
    return await risposta_file(
        services.uploads,
        f"allegati/{allegato['nome_file']}",
        allegato["tipo_mime"],
    )


@app.get("/lavori")
async def leggi_lavori(services: CloudflareServices = Depends(get_services)):
    lavori = await D1Store(services.database).all(
        "SELECT id, titolo, descrizione, localita, data_creazione "
        "FROM lavori ORDER BY data_creazione DESC"
    )
    return {
        "dati": [
            {
                "id": lavoro["id"],
                "titolo": lavoro["titolo"],
                "descrizione": lavoro["descrizione"] or "",
                "localita": lavoro["localita"] or "",
                "immagine_url": f"/api/lavori/{lavoro['id']}/immagine",
                "data_creazione": valore_data_iso(lavoro["data_creazione"]),
            }
            for lavoro in lavori
        ]
    }


@app.get("/lavori/{lavoro_id}/immagine")
async def leggi_immagine_lavoro(
    lavoro_id: int,
    services: CloudflareServices = Depends(get_services),
):
    lavoro = await D1Store(services.database).one(
        "SELECT nome_file, tipo_mime FROM lavori WHERE id = ? LIMIT 1",
        lavoro_id,
    )
    if not lavoro:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")
    return await risposta_file(
        services.uploads,
        f"lavori/{lavoro['nome_file']}",
        lavoro["tipo_mime"],
    )


@app.post("/lavori", status_code=201)
async def crea_lavoro(
    titolo: str = Form(...),
    descrizione: str = Form(default=""),
    localita: str = Form(default=""),
    immagine: UploadFile = File(...),
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    titolo = titolo.strip()
    descrizione = descrizione.strip()
    localita = localita.strip()
    if not titolo or len(titolo) > 160:
        raise HTTPException(
            status_code=422,
            detail="Il titolo è obbligatorio e non può superare 160 caratteri.",
        )
    if len(descrizione) > 3000 or len(localita) > 160:
        raise HTTPException(status_code=422, detail="Descrizione o località troppo lunghe.")

    contenuto = await immagine.read(MAX_UPLOAD_SIZE + 1)
    if not contenuto:
        raise HTTPException(status_code=400, detail="Seleziona un’immagine da caricare.")
    if len(contenuto) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="L’immagine non può superare 10 MB.")
    tipo = tipo_immagine(contenuto)
    if not tipo:
        raise HTTPException(status_code=415, detail="Sono consentite solo immagini JPG, PNG o WEBP.")

    tipo_mime, estensione = tipo
    nome_file = f"{uuid.uuid4().hex}{estensione}"
    nome_originale = os.path.basename((immagine.filename or "immagine").replace("\\", "/"))[:255]
    chiave = f"lavori/{nome_file}"
    await salva_su_r2(services.uploads, chiave, contenuto)
    try:
        lavoro = await D1Store(services.database).one(
            "INSERT INTO lavori "
            "(titolo, descrizione, localita, nome_file, nome_originale, tipo_mime, data_creazione) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id",
            titolo,
            descrizione,
            localita,
            nome_file,
            nome_originale,
            tipo_mime,
            datetime.now(timezone.utc).isoformat(),
        )
        if lavoro is None:
            raise RuntimeError("D1 non ha restituito l'identificativo del lavoro creato.")
    except Exception:
        await elimina_da_r2(services.uploads, chiave)
        raise
    return {"id": lavoro["id"], "titolo": titolo}


@app.put("/lavori/{lavoro_id}/immagine")
async def sostituisci_immagine_lavoro(
    lavoro_id: int,
    immagine: UploadFile = File(...),
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    store = D1Store(services.database)
    lavoro = await store.one(
        "SELECT nome_file, titolo FROM lavori WHERE id = ? LIMIT 1", lavoro_id
    )
    if not lavoro:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    contenuto = await immagine.read(MAX_UPLOAD_SIZE + 1)
    if not contenuto:
        raise HTTPException(status_code=400, detail="Seleziona un’immagine da caricare.")
    if len(contenuto) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="L’immagine non può superare 10 MB.")
    tipo = tipo_immagine(contenuto)
    if not tipo:
        raise HTTPException(status_code=415, detail="Sono consentite solo immagini JPG, PNG o WEBP.")

    tipo_mime, estensione = tipo
    nuovo_nome_file = f"{uuid.uuid4().hex}{estensione}"
    nuova_chiave = f"lavori/{nuovo_nome_file}"
    vecchia_chiave = f"lavori/{lavoro['nome_file']}"
    nome_originale = os.path.basename((immagine.filename or "immagine").replace("\\", "/"))[:255]
    await salva_su_r2(services.uploads, nuova_chiave, contenuto)
    try:
        await store.run(
            "UPDATE lavori SET nome_file = ?, nome_originale = ?, tipo_mime = ? WHERE id = ?",
            nuovo_nome_file,
            nome_originale,
            tipo_mime,
            lavoro_id,
        )
    except Exception:
        await elimina_da_r2(services.uploads, nuova_chiave)
        raise
    await elimina_da_r2(services.uploads, vecchia_chiave)
    return {"id": lavoro_id, "titolo": lavoro["titolo"]}


COLONNE_LAVORO_VALIDE: dict[str, int] = {
    "titolo": 160,
    "descrizione": 3000,
    "localita": 160,
}


@app.patch("/lavori/{lavoro_id}")
async def aggiorna_lavoro(
    lavoro_id: int,
    modifiche: LavoroAggiornamento,
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    store = D1Store(services.database)
    lavoro = await store.one(
        "SELECT id, titolo, descrizione, localita FROM lavori WHERE id = ? LIMIT 1",
        lavoro_id,
    )
    if not lavoro:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    valori = modifiche.model_dump(exclude_unset=True)
    aggiornamenti = {}
    for campo, valore in valori.items():
        if campo not in COLONNE_LAVORO_VALIDE:
            raise HTTPException(status_code=422, detail=f"Campo non consentito: {campo}")
        if valore is None:
            continue
        valore = valore.strip()
        limite = COLONNE_LAVORO_VALIDE[campo]
        if len(valore) > limite or (campo == "titolo" and not valore):
            raise HTTPException(status_code=422, detail=f"Valore non valido per {campo}.")
        aggiornamenti[campo] = valore
    if aggiornamenti:
        # Costruisce la query SQL solo con colonne verificate dalla whitelist immutabile
        clausole = [f"{colonna} = ?" for colonna in COLONNE_LAVORO_VALIDE if colonna in aggiornamenti]
        parametri = [aggiornamenti[colonna] for colonna in COLONNE_LAVORO_VALIDE if colonna in aggiornamenti]
        colonne_sql = ", ".join(clausole)
        await store.run(
            f"UPDATE lavori SET {colonne_sql} WHERE id = ?",
            *parametri,
            lavoro_id,
        )
    return {
        "id": lavoro_id,
        "titolo": aggiornamenti.get("titolo", lavoro["titolo"]),
    }


@app.delete("/lavori/{lavoro_id}", status_code=204)
async def elimina_lavoro(
    lavoro_id: int,
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    store = D1Store(services.database)
    lavoro = await store.one(
        "SELECT nome_file FROM lavori WHERE id = ? LIMIT 1", lavoro_id
    )
    if not lavoro:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")
    await store.run("DELETE FROM lavori WHERE id = ?", lavoro_id)
    await elimina_da_r2(services.uploads, f"lavori/{lavoro['nome_file']}")
