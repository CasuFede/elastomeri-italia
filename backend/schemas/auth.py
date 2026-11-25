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


class ClienteConfirmResetRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    password: str = Field(min_length=8, max_length=200)


class ClienteModificaPassword(BaseModel):
    password: str = Field(min_length=12, max_length=200)


class ClienteCambiaPasswordForm(BaseModel):
    password: str = Field(min_length=8, max_length=200)


class ClienteCreazione(BaseModel):
    nome: str = Field(min_length=1, max_length=160)
    email: EmailStr
    password: Optional[str] = Field(default=None, max_length=200)
