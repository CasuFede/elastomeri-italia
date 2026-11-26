"""Schemi Pydantic per gestione completa dei lavori e della stratigrafia."""
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class StratigrafiaStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fase: str = Field(default="", max_length=16)
    titolo: str = Field(..., min_length=1, max_length=160)
    dettaglio: str = Field(default="", max_length=1000)


class LavoroCreazione(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titolo: str = Field(..., min_length=1, max_length=160)
    categoria: str = Field(default="Impermeabilizzazioni", max_length=80)
    localita: str = Field(default="", max_length=160)
    superficie_mq: int = Field(default=0, ge=0, le=1_000_000)
    supporto: str = Field(default="", max_length=160)
    ciclo_sistema: str = Field(default="", max_length=160)
    armatura: str = Field(default="", max_length=160)
    applicazione: str = Field(default="", max_length=160)
    descrizione: str = Field(default="", max_length=3000)
    stratigrafia_descrizione: str = Field(default="", max_length=3000)
    stratigrafia_fasi: list[StratigrafiaStep] = Field(default_factory=list, max_length=12)


class LavoroAggiornamento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titolo: Optional[str] = Field(default=None, max_length=160)
    categoria: Optional[str] = Field(default=None, max_length=80)
    localita: Optional[str] = Field(default=None, max_length=160)
    superficie_mq: Optional[int] = Field(default=None, ge=0, le=1_000_000)
    supporto: Optional[str] = Field(default=None, max_length=160)
    ciclo_sistema: Optional[str] = Field(default=None, max_length=160)
    armatura: Optional[str] = Field(default=None, max_length=160)
    applicazione: Optional[str] = Field(default=None, max_length=160)
    descrizione: Optional[str] = Field(default=None, max_length=3000)
    stratigrafia_descrizione: Optional[str] = Field(default=None, max_length=3000)
    stratigrafia_fasi: Optional[list[StratigrafiaStep]] = Field(default=None, max_length=12)
