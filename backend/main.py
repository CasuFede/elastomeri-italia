import os
import httpx
import secrets
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

app = FastAPI(title="API Elastomeri Italia")

# --- CONFIGURAZIONE DATABASE SQLITE ---
# Il file preventivi.db verrà creato direttamente nella cartella backend
SQLALCHEMY_DATABASE_URL = "sqlite:///./preventivi.db"

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
    data_richiesta = Column(DateTime, default=datetime.utcnow)

# Crea la tabella all'avvio se non esiste
Base.metadata.create_all(bind=engine)

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

async def invia_notifica_telegram(dati: PreventivoRequest):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Errore: Credenziali Telegram mancanti nel file .env")
        return

    testo_messaggio = (
        f"🚀 <b>Nuovo Preventivo Elastomeri Italia!</b>\n\n"
        f"👤 <b>Nome:</b> {dati.nome}\n"
        f"📧 <b>Email:</b> {dati.email}\n"
        f"📞 <b>Telefono:</b> {dati.telefono}\n"
        f"🛠 <b>Servizio:</b> {dati.servizio}\n"
        f"💬 <b>Messaggio:</b>\n{dati.messaggio or 'Nessun messaggio specificato'}"
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
@app.post("/preventivo")
async def richiedi_preventivo(
    dati: PreventivoRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    # 1. Salva la richiesta nel database SQLite
    nuovo_preventivo = PreventivoDB(
        nome=dati.nome,
        email=dati.email,
        telefono=dati.telefono,
        servizio=dati.servizio,
        messaggio=dati.messaggio
    )
    db.add(nuovo_preventivo)
    db.commit()
    db.refresh(nuovo_preventivo) # Aggiorna l'oggetto con l'ID autogenerato
    
    # 2. Invia la notifica Telegram in background
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
            "data_richiesta": p.data_richiesta.isoformat() if p.data_richiesta else None
        })
    
    return {
        "status": "success",
        "autenticato_come": username,
        "totale_richieste": len(lista_dati),
        "dati": lista_dati
    }