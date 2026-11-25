"""Router per la gestione dei preventivi (invio, consultazione, cambio stato, allegati)."""
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from pydantic import EmailStr

from core.config import (
    MAX_UPLOAD_COUNT,
    MAX_UPLOAD_SIZE,
    STATI_PREVENTIVO,
    TELEFONO_REGEX,
    get_secret,
)
from core.database import (
    CloudflareServices,
    D1Store,
    get_environment,
    get_services,
    valore_data_iso,
)
from core.rate_limit import check_rate_limit_d1, get_client_ip
from core.storage import elimina_da_r2, risposta_file, salva_su_r2, tipo_immagine
from api.deps import verifica_credenziali
from schemas.preventivi import PreventivoRequest, StatoPreventivoAggiornamento
from services.email import (
    invia_email_chiarimenti_preventivo,
    invia_email_conferma_preventivo,
)
from services.telegram import invia_notifica_telegram

router = APIRouter(tags=["preventivi"])


@router.post("/preventivo")
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
    website: Optional[str] = Form(default=None),
    files: Optional[list[UploadFile]] = File(default=None),
    services: CloudflareServices = Depends(get_services),
):
    # Campo honeypot anti-bot: i visitatori reali lasciano vuoto questo campo invisibile
    if website and website.strip():
        return {"status": "success", "message": "Richiesta ricevuta", "id_pratica": 0}

    ip = get_client_ip(request)
    store = D1Store(services.database)
    if not await check_rate_limit_d1(store, "preventivo", ip, max_requests=5, window_seconds=600):
        raise HTTPException(
            status_code=429,
            detail="Hai inviato troppe richieste in poco tempo. Attendi qualche minuto prima di riprovare.",
        )

    scelte = {
        "tipo_immobile": (
            tipo_immobile,
            {"Condominio", "Casa indipendente", "Capannone industriale"},
        ),
        "area_intervento": (
            area_intervento,
            {
                "Terrazzi / Balconi",
                "Tetti / Sottotetto",
                "Fondazioni / Cantine",
                "Altro",
            },
        ),
        "situazione": (
            situazione,
            {
                "Infiltrazione attiva (emergenza)",
                "Manutenzione preventiva",
                "Nuova costruzione",
            },
        ),
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

    cifre_telefono = re.sub(r"\D", "", telefono)
    if not TELEFONO_REGEX.match(telefono) or len(cifre_telefono) < 8:
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
            raise HTTPException(
                status_code=413, detail="Le foto superano il limite totale di 10 MB."
            )
        totale_byte += len(contenuto)
        tipo = tipo_immagine(contenuto)
        if not tipo:
            raise HTTPException(
                status_code=415,
                detail="Sono consentite solo immagini JPG, PNG o WEBP.",
            )
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
        dati.nome,
        dati.email,
        dati.telefono,
        dati.servizio,
        dati.messaggio,
        get_secret(environment, "TELEGRAM_BOT_TOKEN"),
        get_secret(environment, "TELEGRAM_CHAT_ID"),
    )
    background_tasks.add_task(
        invia_email_conferma_preventivo,
        dati,
        id_preventivo,
        len(allegati_preparati),
        environment,
    )
    return {
        "status": "success",
        "message": "Richiesta ricevuta",
        "id_pratica": preventivo["id"],
    }


@router.get("/preventivi")
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


@router.patch("/preventivi/{preventivo_id}/stato")
async def aggiorna_stato_preventivo(
    preventivo_id: int,
    modifiche: StatoPreventivoAggiornamento,
    request: Request,
    background_tasks: BackgroundTasks,
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
        "SELECT id, nome, email, servizio, stato, note_cliente FROM preventivi WHERE id = ? LIMIT 1",
        preventivo_id,
    )
    if not preventivo:
        raise HTTPException(status_code=404, detail="Preventivo non trovato.")

    vecchie_note = (preventivo.get("note_cliente") or "").strip()

    await store.run(
        "UPDATE preventivi SET stato = ?, note_cliente = ? WHERE id = ?",
        modifiche.stato,
        note_cliente,
        preventivo_id,
    )

    invia_notifica = False
    if modifiche.invia_email is True:
        invia_notifica = bool(note_cliente)
    elif modifiche.invia_email is False:
        invia_notifica = False
    else:
        invia_notifica = bool(note_cliente) and (note_cliente != vecchie_note)

    if invia_notifica and preventivo.get("email"):
        environment = get_environment(request)
        try:
            await invia_email_chiarimenti_preventivo(
                preventivo.get("nome") or "Cliente",
                preventivo["email"],
                preventivo_id,
                preventivo.get("servizio") or "Intervento",
                note_cliente,
                environment,
            )
        except Exception as exc:
            print(f"Errore invio email chiarimenti: {exc}")

    return {
        "id": preventivo_id,
        "stato": modifiche.stato,
        "note_cliente": note_cliente,
        "email_inviata": invia_notifica,
    }


@router.delete("/preventivi/{preventivo_id}")
async def elimina_preventivo(
    preventivo_id: int,
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    store = D1Store(services.database)
    preventivo = await store.one(
        "SELECT id, nome, email FROM preventivi WHERE id = ? LIMIT 1", preventivo_id
    )
    if not preventivo:
        raise HTTPException(status_code=404, detail="Preventivo non trovato.")

    allegati = await store.all(
        "SELECT nome_file FROM allegati WHERE preventivo_id = ?", preventivo_id
    )
    for allegato in allegati:
        await elimina_da_r2(services.uploads, f"allegati/{allegato['nome_file']}")

    await store.run("DELETE FROM allegati WHERE preventivo_id = ?", preventivo_id)
    await store.run("DELETE FROM preventivi WHERE id = ?", preventivo_id)

    return {
        "status": "success",
        "message": f"Richiesta preventivo #{preventivo_id} eliminata definitivamente.",
        "id": preventivo_id,
    }


@router.get("/preventivi/{preventivo_id}/allegati/{allegato_id}")
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
