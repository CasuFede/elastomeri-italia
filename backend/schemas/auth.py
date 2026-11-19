"""Schemi Pydantic per autenticazione Admin e Area Clienti."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class ClienteLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class ClienteLostPasswordRequest(BaseModel):
    email: EmailStr


class ClienteModificaPassword(BaseModel):
    password: str


class ClienteCambiaPasswordForm(BaseModel):
    password: str


class ClienteCreazione(BaseModel):
    nome: str
    email: EmailStr
    password: Optional[str] = None
