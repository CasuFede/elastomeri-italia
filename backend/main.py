"""Poliurea System API - Modular FastAPI Backend.

Architettura modulare:
- core/: configurazione, sicurezza, database (Cloudflare D1), rate limiter, storage (R2)
- services/: servizi asincroni di notifica email (SMTP/Brevo) e Telegram
- schemas/: validazione Pydantic per input/output API
- api/deps: dipendenze FastAPI per autenticazione Admin e Clienti
- api/routers/: router modulari per dominio (auth, preventivi, clienti, lavori, chat)
"""
import json
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, chat, clienti, lavori, preventivi

# Re-export per compatibilità retroattiva con script o tooling di migrazione
from core.security import crea_hash_password, verifica_hash_password  # noqa: F401

app = FastAPI(
    title="Poliurea System API",
    description="API backend per Poliurea System & Impermeabilizzazioni",
    version="2.0.0",
)

# Configurazione CORS restrittiva ed esplicita
ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://localhost:4321",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:4321",
    "https://poliureasystem.it",
    "https://www.poliureasystem.it",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def remove_api_prefix_and_security(request: Request, call_next: Any) -> Response:
    """Middleware per gestione prefisso /api, HEAD requests, CSRF protection e security headers."""
    is_head = request.method == "HEAD"
    if is_head:
        request.scope["method"] = "GET"

    path = request.scope["path"]
    if path == "/api":
        request.scope["path"] = "/"
        request.scope["raw_path"] = b"/"
    elif path.startswith("/api/"):
        api_path = path[4:]
        request.scope["path"] = api_path
        request.scope["raw_path"] = api_path.encode("utf-8")

    # Protezione CSRF: blocca richieste cross-site mutative che sfruttano cookie di sessione
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        sec_fetch_site = request.headers.get("sec-fetch-site")
        if sec_fetch_site == "cross-site":
            has_auth_cookie = bool(
                request.cookies.get("poliurea_admin_session")
                or request.cookies.get("poliurea_client_session")
            )
            if has_auth_cookie:
                return Response(
                    content=json.dumps({"detail": "Richiesta cross-site non consentita."}),
                    status_code=403,
                    media_type="application/json",
                )

    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"

    if is_head:
        return Response(
            content=b"",
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
    return response


# Inclusione dei router modulari
app.include_router(auth.router)
app.include_router(preventivi.router)
app.include_router(clienti.router)
app.include_router(lavori.router)
app.include_router(chat.router)


@app.get("/health")
async def health_check():
    """Endpoint di healthcheck del servizio API."""
    return {"status": "ok", "service": "poliurea-api", "version": "2.0.0"}
