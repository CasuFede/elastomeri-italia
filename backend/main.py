import os
import httpx
import secrets
import hashlib
import html
import uuid
from pathlib import Path
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy import create_engine, Column, ForeignKey, Integer, String, Text, DateTime, Boolean, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

app = FastAPI(title="API Poliurea System")

# --- CONFIGURAZIONE DATABASE SQLITE ---
# Il file preventivi.db verrà creato direttamente nella cartella backend
SQLALCHEMY_DATABASE_URL = "sqlite:///./preventivi.db"
UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
LAVORI_DIR = UPLOADS_DIR / "lavori"
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

# check_same_thread=False è necessario per SQLite in FastAPI
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Definizione della tabella
class PreventivoDB(Base):
    __tablename__ = "preventivi"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    email = Column(String)
    telefono = Column(String)
    servizio = Column(String)
    messaggio = Column(Text, nullable=True)
    stato = Column(String(40), nullable=False, default="ricevuto", server_default="ricevuto")
    note_cliente = Column(Text, nullable=False, default="", server_default="")
    data_richiesta = Column(DateTime, default=datetime.utcnow)
    allegati = relationship("AllegatoDB", cascade="all, delete-orphan")

class AllegatoDB(Base):
    __tablename__ = "allegati"

    id = Column(Integer, primary_key=True, index=True)
    preventivo_id = Column(Integer, ForeignKey("preventivi.id"), nullable=False)
    nome_file = Column(String, nullable=False)
    nome_originale = Column(String, nullable=False)
    tipo_mime = Column(String, nullable=False)

class LavoroDB(Base):
    __tablename__ = "lavori"

    id = Column(Integer, primary_key=True, index=True)
    titolo = Column(String(160), nullable=False)
    descrizione = Column(Text, nullable=True)
    localita = Column(String(160), nullable=True)
    nome_file = Column(String, nullable=False)
    nome_originale = Column(String, nullable=False)
    tipo_mime = Column(String, nullable=False)
    data_creazione = Column(DateTime, default=datetime.utcnow, nullable=False)

class ClienteDB(Base):
    __tablename__ = "clienti"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(160), nullable=False)
    email = Column(String(254), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    attivo = Column(Boolean, nullable=False, default=True)
    data_creazione = Column(DateTime, default=datetime.utcnow, nullable=False)

# Crea la tabella all'avvio se non esiste
Base.metadata.create_all(bind=engine)

# Aggiunge i campi di stato anche ai database preventivi.db gia esistenti.
with engine.begin() as connection:
    colonne_preventivi = {riga[1] for riga in connection.exec_driver_sql("PRAGMA table_info(preventivi)")}
    if "stato" not in colonne_preventivi:
        connection.exec_driver_sql("ALTER TABLE preventivi ADD COLUMN stato VARCHAR(40) NOT NULL DEFAULT 'ricevuto'")
    if "note_cliente" not in colonne_preventivi:
        connection.exec_driver_sql("ALTER TABLE preventivi ADD COLUMN note_cliente TEXT NOT NULL DEFAULT ''")

# Dipendenza per ottenere la sessione del database per ogni richiesta
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- CONFIGURAZIONE TELEGRAM ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

class PreventivoRequest(BaseModel):
    nome: str
    email: EmailStr
    telefono: str
    servizio: str
    messaggio: Optional[str] = None

class LavoroAggiornamento(BaseModel):
    titolo: Optional[str] = None
    descrizione: Optional[str] = None
    localita: Optional[str] = None

class ClienteCreazione(BaseModel):
    nome: str
    email: EmailStr
    password: str

class StatoPreventivoAggiornamento(BaseModel):
    stato: str
    note_cliente: Optional[str] = ""

async def invia_notifica_telegram(dati: PreventivoRequest):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Errore: Credenziali Telegram mancanti nel file .env")
        return

    testo_messaggio = (
        f"🚀 <b>Nuovo Preventivo Poliurea System!</b>\n\n"
        f"👤 <b>Nome:</b> {html.escape(dati.nome)}\n"
        f"📧 <b>Email:</b> {html.escape(str(dati.email))}\n"
        f"📞 <b>Telefono:</b> {html.escape(dati.telefono)}\n"
        f"🛠 <b>Servizio:</b> {html.escape(dati.servizio)}\n"
        f"💬 <b>Messaggio:</b>\n{html.escape(dati.messaggio or 'Nessun messaggio specificato')}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": testo_messaggio,
        "parse_mode": "HTML"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        except Exception as e:
            print(f"Errore durante l'invio a Telegram: {e}")

# --- ENDPOINT ---
def tipo_immagine(contenuto: bytes) -> Optional[tuple[str, str]]:
    if contenuto.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if contenuto.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if len(contenuto) >= 12 and contenuto[:4] == b"RIFF" and contenuto[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None

@app.post("/preventivo")
async def richiedi_preventivo(
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
    db: Session = Depends(get_db)
):
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
        raise HTTPException(status_code=400, detail="È necessario accettare il trattamento dei dati per inviare la richiesta.")

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
            raise HTTPException(status_code=413, detail=f"Puoi allegare al massimo {MAX_UPLOAD_COUNT} foto.")

    servizio = f"{area_intervento} · {tipo_immobile}"
    dettagli = [
        f"Situazione: {situazione}",
        f"Metratura: {metratura}",
        f"Comune dell'intervento: {comune.strip()}",
    ]
    if messaggio and messaggio.strip():
        dettagli.extend(["", f"Note: {messaggio.strip()}"])
    dati = PreventivoRequest(
        nome=nome.strip(),
        email=email,
        telefono=telefono.strip(),
        servizio=servizio,
        messaggio="\n".join(dettagli),
    )

    nuovo_preventivo = PreventivoDB(
        nome=dati.nome,
        email=str(dati.email),
        telefono=dati.telefono,
        servizio=dati.servizio,
        messaggio=dati.messaggio
    )
    file_salvati = []
    try:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        for contenuto, nome_originale, (tipo_mime, estensione) in allegati_preparati:
            nome_file = f"{uuid.uuid4().hex}{estensione}"
            (UPLOADS_DIR / nome_file).write_bytes(contenuto)
            file_salvati.append(UPLOADS_DIR / nome_file)
            nuovo_preventivo.allegati.append(AllegatoDB(
                nome_file=nome_file,
                nome_originale=nome_originale,
                tipo_mime=tipo_mime,
            ))
        db.add(nuovo_preventivo)
        db.commit()
        db.refresh(nuovo_preventivo)
    except Exception:
        db.rollback()
        for percorso in file_salvati:
            percorso.unlink(missing_ok=True)
        raise

    background_tasks.add_task(invia_notifica_telegram, dati)

    return {
        "status": "success",
        "message": "Richiesta ricevuta",
        "id_pratica": nuovo_preventivo.id
    }

# --- CONFIGURAZIONE AUTENTICAZIONE ---
security = HTTPBasic()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

def verifica_credenziali(credentials: HTTPBasicCredentials = Depends(security)):
    # L'uso di secrets.compare_digest previene gli attacchi basati sulle tempistiche (timing attacks)
    is_username_correct = secrets.compare_digest(credentials.username.encode("utf8"), ADMIN_USERNAME.encode("utf8"))
    is_password_correct = secrets.compare_digest(credentials.password.encode("utf8"), ADMIN_PASSWORD.encode("utf8"))
    
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=401,
            detail="Credenziali non valide",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

def crea_hash_password(password: str) -> str:
    sale = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf8"), sale, PASSWORD_ITERATIONS)
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

def verifica_cliente(
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> ClienteDB:
    email = credentials.username.strip().lower()
    cliente = db.query(ClienteDB).filter(func.lower(ClienteDB.email) == email).first()
    if not cliente or not cliente.attivo or not verifica_hash_password(credentials.password, cliente.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Credenziali cliente non valide",
            headers={"WWW-Authenticate": "Basic"},
        )
    return cliente

# --- ENDPOINT LETTURA STORICO ---
@app.get("/preventivi")
def leggi_preventivi(
    username: str = Depends(verifica_credenziali), 
    db: Session = Depends(get_db)
):
    preventivi = db.query(PreventivoDB).order_by(PreventivoDB.data_richiesta.desc()).all()
    
    # Convertiamo gli oggetti complessi del database in dizionari semplici (JSON serializzabili)
    lista_dati = []
    for p in preventivi:
        lista_dati.append({
            "id": p.id,
            "nome": p.nome,
            "email": p.email,
            "telefono": p.telefono,
            "servizio": p.servizio,
            "messaggio": p.messaggio,
            "stato": p.stato,
            "note_cliente": p.note_cliente,
            "data_richiesta": p.data_richiesta.isoformat() if p.data_richiesta else None,
            "allegati": [
                {"id": a.id, "nome": a.nome_originale}
                for a in p.allegati
            ],
        })
    
    return {
        "status": "success",
        "autenticato_come": username,
        "totale_richieste": len(lista_dati),
        "dati": lista_dati
    }

@app.get("/clienti")
def leggi_clienti(
    username: str = Depends(verifica_credenziali),
    db: Session = Depends(get_db),
):
    clienti = db.query(ClienteDB).order_by(ClienteDB.data_creazione.desc()).all()
    return {
        "dati": [
            {
                "id": cliente.id,
                "nome": cliente.nome,
                "email": cliente.email,
                "attivo": cliente.attivo,
                "preventivi": db.query(PreventivoDB).filter(
                    func.lower(PreventivoDB.email) == cliente.email
                ).count(),
            }
            for cliente in clienti
        ]
    }

@app.post("/clienti", status_code=201)
def crea_cliente(
    dati: ClienteCreazione,
    username: str = Depends(verifica_credenziali),
    db: Session = Depends(get_db),
):
    nome = dati.nome.strip()
    email = str(dati.email).strip().lower()
    if not nome or len(nome) > 160:
        raise HTTPException(status_code=422, detail="Il nome è obbligatorio e non può superare 160 caratteri.")
    if len(dati.password) < 12:
        raise HTTPException(status_code=422, detail="La password iniziale deve contenere almeno 12 caratteri.")
    if db.query(ClienteDB).filter(func.lower(ClienteDB.email) == email).first():
        raise HTTPException(status_code=409, detail="Esiste già un account per questa email.")

    cliente = ClienteDB(nome=nome, email=email, password_hash=crea_hash_password(dati.password))
    db.add(cliente)
    try:
        db.commit()
        db.refresh(cliente)
    except Exception:
        db.rollback()
        raise
    return {"id": cliente.id, "nome": cliente.nome, "email": cliente.email, "attivo": cliente.attivo}

@app.patch("/preventivi/{preventivo_id}/stato")
def aggiorna_stato_preventivo(
    preventivo_id: int,
    modifiche: StatoPreventivoAggiornamento,
    username: str = Depends(verifica_credenziali),
    db: Session = Depends(get_db),
):
    if modifiche.stato not in STATI_PREVENTIVO:
        raise HTTPException(status_code=422, detail="Stato del preventivo non valido.")
    note_cliente = (modifiche.note_cliente or "").strip()
    if len(note_cliente) > 1200:
        raise HTTPException(status_code=422, detail="Le indicazioni al cliente non possono superare 1200 caratteri.")
    preventivo = db.query(PreventivoDB).filter(PreventivoDB.id == preventivo_id).first()
    if not preventivo:
        raise HTTPException(status_code=404, detail="Preventivo non trovato.")
    preventivo.stato = modifiche.stato
    preventivo.note_cliente = note_cliente
    db.commit()
    return {"id": preventivo.id, "stato": preventivo.stato, "note_cliente": preventivo.note_cliente}

@app.get("/area-clienti")
def leggi_area_cliente(
    cliente: ClienteDB = Depends(verifica_cliente),
    db: Session = Depends(get_db),
):
    preventivi = db.query(PreventivoDB).filter(
        func.lower(PreventivoDB.email) == cliente.email
    ).order_by(PreventivoDB.data_richiesta.desc()).all()
    return {
        "cliente": {"nome": cliente.nome, "email": cliente.email},
        "dati": [
            {
                "id": preventivo.id,
                "servizio": preventivo.servizio,
                "messaggio": preventivo.messaggio or "",
                "stato": preventivo.stato,
                "stato_label": STATI_PREVENTIVO.get(preventivo.stato, STATI_PREVENTIVO["ricevuto"]),
                "note_cliente": preventivo.note_cliente or "",
                "data_richiesta": preventivo.data_richiesta.isoformat() if preventivo.data_richiesta else None,
                "allegati": [
                    {"id": allegato.id, "nome": allegato.nome_originale}
                    for allegato in preventivo.allegati
                ],
            }
            for preventivo in preventivi
        ],
    }

@app.get("/area-clienti/preventivi/{preventivo_id}/allegati/{allegato_id}")
def leggi_allegato_cliente(
    preventivo_id: int,
    allegato_id: int,
    cliente: ClienteDB = Depends(verifica_cliente),
    db: Session = Depends(get_db),
):
    preventivo = db.query(PreventivoDB).filter(
        PreventivoDB.id == preventivo_id,
        func.lower(PreventivoDB.email) == cliente.email,
    ).first()
    if not preventivo:
        raise HTTPException(status_code=404, detail="Preventivo non trovato.")
    allegato = db.query(AllegatoDB).filter(
        AllegatoDB.id == allegato_id,
        AllegatoDB.preventivo_id == preventivo_id,
    ).first()
    if not allegato:
        raise HTTPException(status_code=404, detail="Allegato non trovato.")
    percorso = UPLOADS_DIR / allegato.nome_file
    if not percorso.is_file():
        raise HTTPException(status_code=404, detail="File allegato non disponibile.")
    return FileResponse(percorso, media_type=allegato.tipo_mime)

@app.get("/preventivi/{preventivo_id}/allegati/{allegato_id}")
def leggi_allegato(
    preventivo_id: int,
    allegato_id: int,
    username: str = Depends(verifica_credenziali),
    db: Session = Depends(get_db)
):
    allegato = db.query(AllegatoDB).filter(
        AllegatoDB.id == allegato_id,
        AllegatoDB.preventivo_id == preventivo_id,
    ).first()
    if not allegato:
        raise HTTPException(status_code=404, detail="Allegato non trovato")
    percorso = UPLOADS_DIR / allegato.nome_file
    if not percorso.is_file():
        raise HTTPException(status_code=404, detail="File allegato non disponibile")
    return FileResponse(percorso, media_type=allegato.tipo_mime)

@app.get("/lavori")
def leggi_lavori(db: Session = Depends(get_db)):
    lavori = db.query(LavoroDB).order_by(LavoroDB.data_creazione.desc()).all()
    return {
        "dati": [
            {
                "id": lavoro.id,
                "titolo": lavoro.titolo,
                "descrizione": lavoro.descrizione or "",
                "localita": lavoro.localita or "",
                "immagine_url": f"/api/lavori/{lavoro.id}/immagine",
                "data_creazione": lavoro.data_creazione.isoformat(),
            }
            for lavoro in lavori
        ]
    }

@app.get("/lavori/{lavoro_id}/immagine")
def leggi_immagine_lavoro(lavoro_id: int, db: Session = Depends(get_db)):
    lavoro = db.query(LavoroDB).filter(LavoroDB.id == lavoro_id).first()
    if not lavoro:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")
    percorso = LAVORI_DIR / lavoro.nome_file
    if not percorso.is_file():
        raise HTTPException(status_code=404, detail="Immagine non disponibile")
    return FileResponse(percorso, media_type=lavoro.tipo_mime)

@app.post("/lavori", status_code=201)
async def crea_lavoro(
    titolo: str = Form(...),
    descrizione: str = Form(default=""),
    localita: str = Form(default=""),
    immagine: UploadFile = File(...),
    username: str = Depends(verifica_credenziali),
    db: Session = Depends(get_db),
):
    titolo = titolo.strip()
    descrizione = descrizione.strip()
    localita = localita.strip()
    if not titolo or len(titolo) > 160:
        raise HTTPException(status_code=422, detail="Il titolo è obbligatorio e non può superare 160 caratteri.")
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
    LAVORI_DIR.mkdir(parents=True, exist_ok=True)
    percorso = LAVORI_DIR / nome_file
    percorso.write_bytes(contenuto)
    lavoro = LavoroDB(
        titolo=titolo,
        descrizione=descrizione,
        localita=localita,
        nome_file=nome_file,
        nome_originale=nome_originale,
        tipo_mime=tipo_mime,
    )
    try:
        db.add(lavoro)
        db.commit()
        db.refresh(lavoro)
    except Exception:
        db.rollback()
        percorso.unlink(missing_ok=True)
        raise

    return {"id": lavoro.id, "titolo": lavoro.titolo}

@app.put("/lavori/{lavoro_id}/immagine")
async def sostituisci_immagine_lavoro(
    lavoro_id: int,
    immagine: UploadFile = File(...),
    username: str = Depends(verifica_credenziali),
    db: Session = Depends(get_db),
):
    lavoro = db.query(LavoroDB).filter(LavoroDB.id == lavoro_id).first()
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
    nuovo_percorso = LAVORI_DIR / nuovo_nome_file
    vecchio_percorso = LAVORI_DIR / lavoro.nome_file
    nuovo_percorso.write_bytes(contenuto)
    nome_originale = os.path.basename((immagine.filename or "immagine").replace("\\", "/"))[:255]
    try:
        lavoro.nome_file = nuovo_nome_file
        lavoro.nome_originale = nome_originale
        lavoro.tipo_mime = tipo_mime
        db.commit()
    except Exception:
        db.rollback()
        nuovo_percorso.unlink(missing_ok=True)
        raise
    vecchio_percorso.unlink(missing_ok=True)
    return {"id": lavoro.id, "titolo": lavoro.titolo}

@app.patch("/lavori/{lavoro_id}")
def aggiorna_lavoro(
    lavoro_id: int,
    modifiche: LavoroAggiornamento,
    username: str = Depends(verifica_credenziali),
    db: Session = Depends(get_db),
):
    lavoro = db.query(LavoroDB).filter(LavoroDB.id == lavoro_id).first()
    if not lavoro:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")

    valori = modifiche.dict(exclude_unset=True)
    for campo, valore in valori.items():
        if valore is None:
            continue
        valore = valore.strip()
        limite = 160 if campo in {"titolo", "localita"} else 3000
        if len(valore) > limite or (campo == "titolo" and not valore):
            raise HTTPException(status_code=422, detail=f"Valore non valido per {campo}.")
        setattr(lavoro, campo, valore)
    db.commit()
    return {"id": lavoro.id, "titolo": lavoro.titolo}

@app.delete("/lavori/{lavoro_id}", status_code=204)
def elimina_lavoro(
    lavoro_id: int,
    username: str = Depends(verifica_credenziali),
    db: Session = Depends(get_db),
):
    lavoro = db.query(LavoroDB).filter(LavoroDB.id == lavoro_id).first()
    if not lavoro:
        raise HTTPException(status_code=404, detail="Lavoro non trovato")
    percorso = LAVORI_DIR / lavoro.nome_file
    db.delete(lavoro)
    db.commit()
    percorso.unlink(missing_ok=True)