"""Schemi Pydantic per gestione richieste preventivo."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class PreventivoRequest(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    telefono: str
    servizio: str
    messaggio: Optional[str] = None


class StatoPreventivoAggiornamento(BaseModel):
    stato: str
    note_cliente: Optional[str] = Field(default="", max_length=1200)
    invia_email: Optional[bool] = None
