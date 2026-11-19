"""Schemi Pydantic per gestione galleria lavori."""
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LavoroAggiornamento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titolo: Optional[str] = Field(default=None, max_length=160)
    descrizione: Optional[str] = Field(default=None, max_length=2000)
    localita: Optional[str] = Field(default=None, max_length=120)
