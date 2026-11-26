"""Router per gestione completa dei lavori: scheda tecnica, stratigrafia, galleria prima/dopo e video."""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import ValidationError

from api.deps import verifica_credenziali
from core.config import (
    CATEGORIE_LAVORO_VALIDE,
    COLONNE_LAVORO_VALIDE,
    MAX_UPLOAD_SIZE,
    MAX_VIDEO_UPLOAD_SIZE,
    TIPI_MEDIA_LAVORO_VALIDI,
)
from core.database import CloudflareServices, D1Store, get_services, valore_data_iso
from core.storage import (
    elimina_da_r2,
    risposta_file,
    risposta_media_range,
    salva_su_r2,
    tipo_immagine,
    tipo_video,
)
from schemas.lavori import LavoroAggiornamento, LavoroCreazione, StratigrafiaStep

router = APIRouter(tags=["Lavori Galleria"])


def _normalizza_categoria(valore: Optional[str]) -> str:
    pulito = (valore or "").strip()
    if pulito in CATEGORIE_LAVORO_VALIDE:
        return pulito
    return "Impermeabilizzazioni"


def _serializza_fasi(fasi: list[StratigrafiaStep]) -> str:
    out = []
    for idx, step in enumerate(fasi, start=1):
        titolo = step.titolo.strip()
        dettaglio = step.dettaglio.strip()
        if not titolo:
            continue
        fase = step.fase.strip() or f"{idx:02d}"
        out.append({"fase": fase, "titolo": titolo, "dettaglio": dettaglio})
    return json.dumps(out, ensure_ascii=False)


def _deserializza_fasi(raw: Any) -> list[dict[str, str]]:
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        parsed = json.loads(str(raw))
        if isinstance(parsed, list):
            return [
                {
                    "fase": str(item.get("fase") or f"{idx:02d}"),
                    "titolo": str(item.get("titolo") or ""),
                    "dettaglio": str(item.get("dettaglio") or ""),
                }
                for idx, item in enumerate(parsed, start=1)
                if isinstance(item, dict) and str(item.get("titolo") or "").strip()
            ]
    except Exception:
        pass
    return []


def _formatta_lavoro(lavoro: dict[str, Any], media_rows: list[dict[str, Any]]) -> dict[str, Any]:
    lavoro_id = lavoro["id"]
    foto_prima = []
    foto_dopo = []
    video_dopo = []

    for m in media_rows:
        media_id = m["id"]
        tipo = m["tipo"]
        url = f"/api/lavori/{lavoro_id}/media/{media_id}"
        didascalia = m.get("didascalia") or ""
        titolo_media = m.get("titolo") or ""
        if tipo == "prima":
            foto_prima.append(
                {
                    "id": media_id,
                    "url": url,
                    "alt": didascalia or f"Prima dell'intervento: {lavoro['titolo']}",
                    "didascalia": didascalia,
                    "ordine": int(m.get("ordine") or 0),
                }
            )
        elif tipo == "dopo":
            foto_dopo.append(
                {
                    "id": media_id,
                    "url": url,
                    "alt": didascalia or f"Risultato finale: {lavoro['titolo']}",
                    "didascalia": didascalia,
                    "ordine": int(m.get("ordine") or 0),
                }
            )
        elif tipo == "video":
            poster_file = m.get("poster_file") or ""
            poster_url = (
                f"/api/lavori/{lavoro_id}/media/{media_id}/poster"
                if poster_file
                else ""
            )
            video_dopo.append(
                {
                    "id": media_id,
                    "url": url,
                    "poster_url": poster_url,
                    "titolo": titolo_media or "Video del risultato",
                    "durata": m.get("durata") or "",
                    "descrizione": didascalia,
                    "ordine": int(m.get("ordine") or 0),
                }
            )

    # Compatibilità retroattiva: se un vecchio lavoro ha solo nome_file su lavori e nessun media
    legacy_file = (lavoro.get("nome_file") or "").strip()
    if legacy_file and not foto_prima and not foto_dopo:
        foto_dopo.append(
            {
                "id": 0,
                "url": f"/api/lavori/{lavoro_id}/immagine",
                "alt": f"Lavoro realizzato da Poliurea System: {lavoro['titolo']}",
                "didascalia": lavoro.get("descrizione") or "",
                "ordine": 0,
            }
        )

    cover_url = (
        foto_dopo[0]["url"]
        if foto_dopo
        else (
            foto_prima[0]["url"]
            if foto_prima
            else (f"/api/lavori/{lavoro_id}/immagine" if legacy_file else "")
        )
    )

    # Se un video non ha poster dedicato, usa la prima foto dopo o prima disponibile
    fallback_poster = foto_dopo[0]["url"] if foto_dopo else (foto_prima[0]["url"] if foto_prima else "")
    for v in video_dopo:
        if not v["poster_url"]:
            v["poster_url"] = fallback_poster

    return {
        "id": lavoro_id,
        "titolo": lavoro["titolo"],
        "categoria": _normalizza_categoria(lavoro.get("categoria")),
        "localita": lavoro.get("localita") or "",
        "superficie_mq": int(lavoro.get("superficie_mq") or 0),
        "supporto": lavoro.get("supporto") or "",
        "ciclo_sistema": lavoro.get("ciclo_sistema") or "",
        "armatura": lavoro.get("armatura") or "",
        "applicazione": lavoro.get("applicazione") or "",
        "descrizione": lavoro.get("descrizione") or "",
        "stratigrafia_descrizione": lavoro.get("stratigrafia_descrizione") or "",
        "stratigrafia_fasi": _deserializza_fasi(lavoro.get("stratigrafia_fasi")),
        "foto_prima": foto_prima,
        "foto_dopo": foto_dopo,
        "video_dopo": video_dopo,
        "immagine_url": cover_url,
        "data_creazione": valore_data_iso(lavoro.get("data_creazione")),
    }


@router.get("/lavori")
async def leggi_lavori(services: CloudflareServices = Depends(get_services)):
    store = D1Store(services.database)
    lavori = await store.all(
        "SELECT id, titolo, categoria, descrizione, localita, superficie_mq, "
        "supporto, ciclo_sistema, armatura, applicazione, "
        "stratigrafia_descrizione, stratigrafia_fasi, nome_file, data_creazione "
        "FROM lavori ORDER BY data_creazione DESC, id DESC"
    )
    if not lavori:
        return {"dati": []}

    tutti_media = await store.all(
        "SELECT id, lavoro_id, tipo, titolo, didascalia, durata, poster_file, ordine "
        "FROM lavori_media ORDER BY ordine ASC, id ASC"
    )
    media_per_lavoro: dict[int, list[dict[str, Any]]] = {}
    for riga in tutti_media:
        media_per_lavoro.setdefault(riga["lavoro_id"], []).append(riga)

    return {
        "dati": [
            _formatta_lavoro(lavoro, media_per_lavoro.get(lavoro["id"], []))
            for lavoro in lavori
        ]
    }


@router.get("/lavori/{lavoro_id}/immagine")
async def leggi_immagine_lavoro(
    lavoro_id: int,
    services: CloudflareServices = Depends(get_services),
):
    store = D1Store(services.database)
    lavoro = await store.one(
        "SELECT nome_file, tipo_mime FROM lavori WHERE id = ? LIMIT 1",
        lavoro_id,
    )
    if not lavoro:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    nome_file = (lavoro.get("nome_file") or "").strip()
    if nome_file:
        return await risposta_file(
            services.uploads,
            f"lavori/{nome_file}",
            lavoro["tipo_mime"] or "image/jpeg",
        )

    primo_media = await store.one(
        "SELECT nome_file, tipo_mime FROM lavori_media "
        "WHERE lavoro_id = ? AND tipo IN ('dopo', 'prima') "
        "ORDER BY CASE tipo WHEN 'dopo' THEN 0 ELSE 1 END, ordine ASC, id ASC LIMIT 1",
        lavoro_id,
    )
    if not primo_media:
        raise HTTPException(status_code=404, detail="Immagine non disponibile")
    return await risposta_file(
        services.uploads,
        f"lavori/{lavoro_id}/{primo_media['nome_file']}",
        primo_media["tipo_mime"],
    )


@router.post("/lavori", status_code=201)
async def crea_lavoro(
    request: Request,
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    content_type = (request.headers.get("content-type") or "").lower()
    store = D1Store(services.database)
    ora_iso = datetime.now(timezone.utc).isoformat()

    # Modalità 1: JSON strutturato (nuovo pannello admin completo)
    if "application/json" in content_type:
        try:
            body = await request.json()
            dati = LavoroCreazione.model_validate(body)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()[0].get("msg", "Dati non validi.")) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Payload JSON non valido.") from exc

        titolo = dati.titolo.strip()
        if not titolo:
            raise HTTPException(status_code=422, detail="Il titolo è obbligatorio.")

        lavoro = await store.one(
            "INSERT INTO lavori ("
            "titolo, categoria, descrizione, localita, superficie_mq, "
            "supporto, ciclo_sistema, armatura, applicazione, "
            "stratigrafia_descrizione, stratigrafia_fasi, "
            "nome_file, nome_originale, tipo_mime, data_creazione"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', '', ?) RETURNING id",
            titolo,
            _normalizza_categoria(dati.categoria),
            dati.descrizione.strip(),
            dati.localita.strip(),
            int(dati.superficie_mq),
            dati.supporto.strip(),
            dati.ciclo_sistema.strip(),
            dati.armatura.strip(),
            dati.applicazione.strip(),
            dati.stratigrafia_descrizione.strip(),
            _serializza_fasi(dati.stratigrafia_fasi),
            ora_iso,
        )
        if lavoro is None:
            raise RuntimeError("D1 non ha restituito l'identificativo del lavoro creato.")
        return {"id": lavoro["id"], "titolo": titolo}

    # Modalità 2: Multipart FormData (compatibilità retroattiva con vecchio form singolo)
    form = await request.form()
    titolo = str(form.get("titolo") or "").strip()
    descrizione = str(form.get("descrizione") or "").strip()
    localita = str(form.get("localita") or "").strip()
    categoria = _normalizza_categoria(str(form.get("categoria") or ""))
    try:
        superficie_mq = max(0, int(str(form.get("superficie_mq") or "0").strip() or "0"))
    except ValueError:
        superficie_mq = 0
    supporto = str(form.get("supporto") or "").strip()[:160]
    ciclo_sistema = str(form.get("ciclo_sistema") or "").strip()[:160]
    armatura = str(form.get("armatura") or "").strip()[:160]
    applicazione = str(form.get("applicazione") or "").strip()[:160]
    stratigrafia_descrizione = str(form.get("stratigrafia_descrizione") or "").strip()[:3000]

    if not titolo or len(titolo) > 160:
        raise HTTPException(
            status_code=422,
            detail="Il titolo è obbligatorio e non può superare 160 caratteri.",
        )
    if len(descrizione) > 3000 or len(localita) > 160:
        raise HTTPException(status_code=422, detail="Descrizione o località troppo lunghe.")

    immagine = form.get("immagine")
    nome_file = ""
    nome_originale = ""
    tipo_mime = ""
    chiave = ""

    if isinstance(immagine, UploadFile) and (immagine.filename or ""):
        contenuto = await immagine.read(MAX_UPLOAD_SIZE + 1)
        if not contenuto:
            raise HTTPException(status_code=400, detail="Seleziona un’immagine valida da caricare.")
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
        lavoro = await store.one(
            "INSERT INTO lavori ("
            "titolo, categoria, descrizione, localita, superficie_mq, "
            "supporto, ciclo_sistema, armatura, applicazione, "
            "stratigrafia_descrizione, stratigrafia_fasi, "
            "nome_file, nome_originale, tipo_mime, data_creazione"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', ?, ?, ?, ?) RETURNING id",
            titolo,
            categoria,
            descrizione,
            localita,
            superficie_mq,
            supporto,
            ciclo_sistema,
            armatura,
            applicazione,
            stratigrafia_descrizione,
            nome_file,
            nome_originale,
            tipo_mime,
            ora_iso,
        )
        if lavoro is None:
            raise RuntimeError("D1 non ha restituito l'identificativo del lavoro creato.")
    except Exception:
        if chiave:
            await elimina_da_r2(services.uploads, chiave)
        raise
    return {"id": lavoro["id"], "titolo": titolo}


@router.post("/lavori/{lavoro_id}/media", status_code=201)
async def aggiungi_media_lavoro(
    lavoro_id: int,
    tipo: str = Form(...),
    file: UploadFile = File(...),
    titolo: str = Form(default=""),
    didascalia: str = Form(default=""),
    durata: str = Form(default=""),
    ordine: int = Form(default=0),
    poster: Optional[UploadFile] = File(default=None),
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    tipo_pulito = tipo.strip().lower()
    if tipo_pulito not in TIPI_MEDIA_LAVORO_VALIDI:
        raise HTTPException(
            status_code=422,
            detail="Tipo media non valido. Usa 'prima', 'dopo' o 'video'.",
        )

    store = D1Store(services.database)
    esistente = await store.one("SELECT id FROM lavori WHERE id = ? LIMIT 1", lavoro_id)
    if not esistente:
        raise HTTPException(status_code=404, detail="Lavoro non trovato.")

    limite = MAX_VIDEO_UPLOAD_SIZE if tipo_pulito == "video" else MAX_UPLOAD_SIZE
    contenuto = await file.read(limite + 1)
    if not contenuto:
        raise HTTPException(status_code=400, detail="File vuoto o non valido.")
    if len(contenuto) > limite:
        mb = limite // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"Il file supera il limite massimo di {mb} MB.")

    if tipo_pulito == "video":
        rilevato = tipo_video(contenuto)
        if not rilevato:
            raise HTTPException(
                status_code=415,
                detail="Formato video non supportato. Carica un file MP4 o WEBM.",
            )
    else:
        rilevato = tipo_immagine(contenuto)
        if not rilevato:
            raise HTTPException(
                status_code=415,
                detail="Sono consentite solo immagini JPG, PNG o WEBP.",
            )

    tipo_mime, estensione = rilevato
    nome_file = f"{uuid.uuid4().hex}{estensione}"
    nome_originale = os.path.basename((file.filename or "media").replace("\\", "/"))[:255]
    chiave = f"lavori/{lavoro_id}/{nome_file}"

    poster_file = ""
    poster_mime = ""
    poster_chiave = ""
    if tipo_pulito == "video" and poster is not None and (poster.filename or ""):
        poster_bytes = await poster.read(5 * 1024 * 1024 + 1)
        if poster_bytes and len(poster_bytes) <= 5 * 1024 * 1024:
            p_tipo = tipo_immagine(poster_bytes)
            if p_tipo:
                poster_mime, poster_ext = p_tipo
                poster_file = f"poster-{uuid.uuid4().hex}{poster_ext}"
                poster_chiave = f"lavori/{lavoro_id}/{poster_file}"
                await salva_su_r2(services.uploads, poster_chiave, poster_bytes)

    await salva_su_r2(services.uploads, chiave, contenuto)
    try:
        inserito = await store.one(
            "INSERT INTO lavori_media ("
            "lavoro_id, tipo, nome_file, nome_originale, tipo_mime, "
            "titolo, didascalia, durata, poster_file, poster_mime, ordine, data_creazione"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
            lavoro_id,
            tipo_pulito,
            nome_file,
            nome_originale,
            tipo_mime,
            titolo.strip()[:160],
            didascalia.strip()[:300],
            durata.strip()[:20],
            poster_file,
            poster_mime,
            int(ordine),
            datetime.now(timezone.utc).isoformat(),
        )
        if inserito is None:
            raise RuntimeError("D1 non ha restituito l'identificativo del media caricato.")
    except Exception:
        await elimina_da_r2(services.uploads, chiave)
        if poster_chiave:
            await elimina_da_r2(services.uploads, poster_chiave)
        raise

    media_id = inserito["id"]
    return {
        "id": media_id,
        "tipo": tipo_pulito,
        "url": f"/api/lavori/{lavoro_id}/media/{media_id}",
        "poster_url": f"/api/lavori/{lavoro_id}/media/{media_id}/poster" if poster_file else "",
        "titolo": titolo.strip()[:160],
        "didascalia": didascalia.strip()[:300],
        "durata": durata.strip()[:20],
        "ordine": int(ordine),
    }


@router.get("/lavori/{lavoro_id}/media/{media_id}")
async def leggi_media_lavoro(
    lavoro_id: int,
    media_id: int,
    request: Request,
    services: CloudflareServices = Depends(get_services),
):
    media = await D1Store(services.database).one(
        "SELECT nome_file, tipo_mime FROM lavori_media WHERE id = ? AND lavoro_id = ? LIMIT 1",
        media_id,
        lavoro_id,
    )
    if not media:
        raise HTTPException(status_code=404, detail="Media non trovato.")
    return await risposta_media_range(
        services.uploads,
        f"lavori/{lavoro_id}/{media['nome_file']}",
        media["tipo_mime"],
        range_header=request.headers.get("range"),
    )


@router.get("/lavori/{lavoro_id}/media/{media_id}/poster")
async def leggi_poster_media_lavoro(
    lavoro_id: int,
    media_id: int,
    services: CloudflareServices = Depends(get_services),
):
    media = await D1Store(services.database).one(
        "SELECT poster_file, poster_mime FROM lavori_media WHERE id = ? AND lavoro_id = ? LIMIT 1",
        media_id,
        lavoro_id,
    )
    if not media or not (media.get("poster_file") or "").strip():
        raise HTTPException(status_code=404, detail="Copertina video non trovata.")
    return await risposta_file(
        services.uploads,
        f"lavori/{lavoro_id}/{media['poster_file']}",
        media["poster_mime"] or "image/jpeg",
    )


@router.delete("/lavori/{lavoro_id}/media/{media_id}", status_code=204)
async def elimina_media_lavoro(
    lavoro_id: int,
    media_id: int,
    username: str = Depends(verifica_credenziali),
    services: CloudflareServices = Depends(get_services),
):
    store = D1Store(services.database)
    media = await store.one(
        "SELECT nome_file, poster_file FROM lavori_media WHERE id = ? AND lavoro_id = ? LIMIT 1",
        media_id,
        lavoro_id,
    )
    if not media:
        raise HTTPException(status_code=404, detail="Media non trovato.")
    await store.run("DELETE FROM lavori_media WHERE id = ? AND lavoro_id = ?", media_id, lavoro_id)
    await elimina_da_r2(services.uploads, f"lavori/{lavoro_id}/{media['nome_file']}")
    if media.get("poster_file"):
        await elimina_da_r2(services.uploads, f"lavori/{lavoro_id}/{media['poster_file']}")


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
    vecchio_nome = (lavoro.get("nome_file") or "").strip()
    vecchia_chiave = f"lavori/{vecchio_nome}" if vecchio_nome else ""
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
    if vecchia_chiave:
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
        "SELECT id, titolo FROM lavori WHERE id = ? LIMIT 1",
        lavoro_id,
    )
    if not lavoro:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    valori = modifiche.model_dump(exclude_unset=True)
    clausole: list[str] = []
    parametri: list[Any] = []
    nuovo_titolo = lavoro["titolo"]

    for campo, valore in valori.items():
        if valore is None:
            continue
        if campo == "superficie_mq":
            clausole.append("superficie_mq = ?")
            parametri.append(max(0, int(valore)))
        elif campo == "stratigrafia_fasi":
            step_objs = [
                StratigrafiaStep.model_validate(item) if isinstance(item, dict) else item
                for item in valore
            ]
            clausole.append("stratigrafia_fasi = ?")
            parametri.append(_serializza_fasi(step_objs))
        elif campo in COLONNE_LAVORO_VALIDE:
            testo = str(valore).strip()
            limite = COLONNE_LAVORO_VALIDE[campo]
            if len(testo) > limite or (campo == "titolo" and not testo):
                raise HTTPException(status_code=422, detail=f"Valore non valido per {campo}.")
            if campo == "categoria":
                testo = _normalizza_categoria(testo)
            if campo == "titolo":
                nuovo_titolo = testo
            clausole.append(f"{campo} = ?")
            parametri.append(testo)
        else:
            raise HTTPException(status_code=422, detail=f"Campo non consentito: {campo}")

    if clausole:
        colonne_sql = ", ".join(clausole)
        await store.run(
            f"UPDATE lavori SET {colonne_sql} WHERE id = ?",
            *parametri,
            lavoro_id,
        )
    return {
        "id": lavoro_id,
        "titolo": nuovo_titolo,
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

    media_rows = await store.all(
        "SELECT nome_file, poster_file FROM lavori_media WHERE lavoro_id = ?",
        lavoro_id,
    )
    await store.run("DELETE FROM lavori_media WHERE lavoro_id = ?", lavoro_id)
    await store.run("DELETE FROM lavori WHERE id = ?", lavoro_id)

    legacy_file = (lavoro.get("nome_file") or "").strip()
    if legacy_file:
        await elimina_da_r2(services.uploads, f"lavori/{legacy_file}")
    for m in media_rows:
        await elimina_da_r2(services.uploads, f"lavori/{lavoro_id}/{m['nome_file']}")
        if m.get("poster_file"):
            await elimina_da_r2(services.uploads, f"lavori/{lavoro_id}/{m['poster_file']}")
