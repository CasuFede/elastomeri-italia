"""Router per gestione clienti (amministrazione e portale area clienti)."""
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response

from core.config import STATI_PREVENTIVO, TOKEN_SESSIONE_DURATA, get_secret, get_session_secret
from core.database import (
    CloudflareServices,
    D1Store,
    get_environment,
    get_services,
    valore_data_iso,
)
from core.security import (
    crea_hash_password,
    crea_token_sessione,
    genera_password_casuale,
    is_secure_request,
)
from core.storage import risposta_file
from api.deps import verifica_cliente, verifica_credenziali
from schemas.auth import (
    ClienteCambiaPasswordForm,
    ClienteCreazione,
    ClienteModificaPassword,
)
from services.email import invia_email_credenziali_cliente

router = APIRouter(tags=["clienti"])


# ==============================================================================
# SEZIONE AMMINISTRAZIONE CLIENTI (Richiede admin session)
# ==============================================================================


@router.get("/clienti")
async def leggi_clienti(
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    righe = await D1Store(services.database).all(
        "SELECT c.id, c.nome, c.email, c.attivo, c.data_creazione, COUNT(p.id) AS totale_preventivi "
        "FROM clienti c "
        "LEFT JOIN preventivi p ON lower(c.email) = lower(p.email) "
        "GROUP BY c.id "
        "ORDER BY c.data_creazione DESC"
    )
    return {
        "dati": [
            {
                "id": r["id"],
                "nome": r["nome"],
                "email": r["email"],
                "attivo": bool(r["attivo"]),
                "preventivi": int(r.get("totale_preventivi") or 0),
            }
            for r in righe
        ]
    }


@router.post("/clienti", status_code=201)
async def crea_cliente(
    dati: ClienteCreazione,
    request: Request,
    background_tasks: BackgroundTasks,
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
    password = (dati.password or "").strip()
    if not password:
        password = genera_password_casuale(14)
    elif len(password) < 12:
        raise HTTPException(
            status_code=422,
            detail="La password iniziale deve contenere almeno 12 caratteri.",
        )
    store = D1Store(services.database)
    if await store.one("SELECT id FROM clienti WHERE lower(email) = ? LIMIT 1", email):
        raise HTTPException(status_code=409, detail="Esiste già un account per questa email.")

    cliente = await store.one(
        "INSERT INTO clienti (nome, email, password_hash, attivo, data_creazione, primo_accesso) "
        "VALUES (?, ?, ?, 1, ?, 1) RETURNING id",
        nome,
        email,
        crea_hash_password(password),
        datetime.now(timezone.utc).isoformat(),
    )
    if cliente is None:
        raise RuntimeError("D1 non ha restituito l'identificativo del cliente creato.")

    environment = get_environment(request)
    background_tasks.add_task(
        invia_email_credenziali_cliente,
        nome,
        email,
        password,
        environment,
    )

    return {
        "id": cliente["id"],
        "nome": nome,
        "email": email,
        "attivo": True,
        "primo_accesso": True,
        "password": password,
    }


@router.patch("/clienti/{cliente_id}/password")
async def reimposta_password_cliente(
    cliente_id: int,
    dati: ClienteModificaPassword,
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    if len(dati.password) < 12:
        raise HTTPException(
            status_code=422,
            detail="La nuova password deve contenere almeno 12 caratteri.",
        )
    store = D1Store(services.database)
    cliente = await store.one(
        "SELECT id, email, nome FROM clienti WHERE id = ? LIMIT 1", cliente_id
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente non trovato.")

    nuovo_hash = crea_hash_password(dati.password)
    await store.run(
        "UPDATE clienti SET password_hash = ?, primo_accesso = 1 WHERE id = ?",
        nuovo_hash,
        cliente_id,
    )
    return {
        "status": "success",
        "message": f"Password reimpostata con successo per {cliente['email']}.",
        "cliente": {
            "id": cliente["id"],
            "email": cliente["email"],
            "nome": cliente["nome"],
        },
    }


@router.delete("/clienti/{cliente_id}")
async def elimina_cliente(
    cliente_id: int,
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    store = D1Store(services.database)
    cliente = await store.one(
        "SELECT id, email, nome FROM clienti WHERE id = ? LIMIT 1", cliente_id
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente non trovato.")

    await store.run("DELETE FROM clienti WHERE id = ?", cliente_id)
    return {
        "status": "success",
        "message": f"Account cliente di {cliente['email']} eliminato con successo.",
        "id": cliente_id,
    }


# ==============================================================================
# SEZIONE PORTALE AREA CLIENTI (Autenticato tramite sessione cliente)
# ==============================================================================


@router.get("/area-clienti")
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
        "cliente": {
            "nome": cliente["nome"],
            "email": cliente["email"],
            "primo_accesso": bool(cliente.get("primo_accesso", 1)),
        },
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


@router.get("/area-clienti/preventivi/{preventivo_id}/allegati/{allegato_id}")
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


@router.post("/area-clienti/cambia-password")
async def cambia_password_cliente(
    dati: ClienteCambiaPasswordForm,
    request: Request,
    response: Response,
    cliente: dict[str, Any] = Depends(verifica_cliente),
    services: CloudflareServices = Depends(get_services),
):
    nuova_pwd = dati.password.strip()
    if len(nuova_pwd) < 8:
        raise HTTPException(
            status_code=422,
            detail="La nuova password deve contenere almeno 8 caratteri.",
        )
    ha_maiuscola = any(c.isupper() for c in nuova_pwd)
    ha_minuscola = any(c.islower() for c in nuova_pwd)
    ha_numero = any(c.isdigit() for c in nuova_pwd)
    if not (ha_maiuscola and ha_minuscola and ha_numero):
        raise HTTPException(
            status_code=422,
            detail="La password deve essere sicura: inserisci almeno una lettera maiuscola, una minuscola e un numero.",
        )

    store = D1Store(services.database)
    nuovo_hash = crea_hash_password(nuova_pwd)
    await store.run(
        "UPDATE clienti SET password_hash = ?, primo_accesso = 0 WHERE id = ?",
        nuovo_hash,
        cliente["id"],
    )

    environment = get_environment(request)
    session_secret = get_session_secret(environment)
    if session_secret:
        secret_cliente = f"{session_secret}:{nuovo_hash}"
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
        "message": "Password aggiornata con successo. Benvenuto nella tua Area Clienti!",
    }


@router.delete("/area-clienti/account")
async def elimina_proprio_account(
    response: Response,
    cliente: dict[str, Any] = Depends(verifica_cliente),
    services: CloudflareServices = Depends(get_services),
):
    store = D1Store(services.database)
    await store.run("DELETE FROM clienti WHERE id = ?", cliente["id"])
    response.delete_cookie(key="poliurea_client_session", path="/")
    return {
        "status": "success",
        "message": "Il tuo account è stato cancellato definitivamente.",
    }
