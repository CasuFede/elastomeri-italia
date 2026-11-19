"""Router per gestione dei lavori e immagini della galleria interventi."""
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from api.deps import verifica_credenziali
from core.config import COLONNE_LAVORO_VALIDE, MAX_UPLOAD_SIZE
from core.database import CloudflareServices, D1Store, get_services, valore_data_iso
from core.storage import elimina_da_r2, risposta_file, salva_su_r2, tipo_immagine
from schemas.lavori import LavoroAggiornamento

router = APIRouter(tags=["Lavori Galleria"])


@router.get("/lavori")
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


@router.get("/lavori/{lavoro_id}/immagine")
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


@router.post("/lavori", status_code=201)
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


@router.put("/lavori/{lavoro_id}/immagine")
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


@router.patch("/lavori/{lavoro_id}")
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


@router.delete("/lavori/{lavoro_id}", status_code=204)
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
