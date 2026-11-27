"""Poliurea System API - Modular FastAPI Backend.

Architettura modulare:
- core/: configurazione, sicurezza, database (Cloudflare D1), rate limiter, storage (R2)
- services/: servizi asincroni di notifica email (SMTP/Brevo) e Telegram
- schemas/: validazione Pydantic per input/output API
- api/deps: dipendenze FastAPI per autenticazione Admin e Clienti
- api/routers/: router modulari per dominio (auth, preventivi, clienti, lavori, chat)
"""
import json
import os
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, chat, clienti, lavori, preventivi
from core.config import is_worker_runtime

# Re-export per compatibilità retroattiva con script o tooling di migrazione
from core.security import crea_hash_password, verifica_hash_password  # noqa: F401

_IS_WORKER = is_worker_runtime()
_ENABLE_DOCS = os.environ.get("ENABLE_API_DOCS") == "1" and not _IS_WORKER

app = FastAPI(
    title="Poliurea System API",
    description="API backend per Poliurea System & Impermeabilizzazioni",
    version="2.0.0",
    docs_url="/docs" if _ENABLE_DOCS else None,
    redoc_url="/redoc" if _ENABLE_DOCS else None,
    openapi_url="/openapi.json" if _ENABLE_DOCS else None,
)

# Configurazione CORS restrittiva: origini localhost ammesse solo fuori dal Worker di produzione
PRODUCTION_ORIGINS = [
    "https://poliureasystem.it",
    "https://www.poliureasystem.it",
]
DEV_ORIGINS = [
    "http://localhost:8080",
    "http://localhost:4321",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:4321",
]
ALLOWED_ORIGINS = (
    PRODUCTION_ORIGINS
    if (_IS_WORKER and os.environ.get("ALLOW_DEV_ORIGINS") != "1")
    else PRODUCTION_ORIGINS + DEV_ORIGINS
)
ALLOWED_ORIGINS_SET = set(ALLOWED_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
)


def _origin_da_referer(referer: str) -> str:
    try:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        pass
    return ""


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
        has_auth_cookie = bool(
            request.cookies.get("poliurea_admin_session")
            or request.cookies.get("poliurea_client_session")
        )
        if has_auth_cookie:
            sec_fetch_site = (request.headers.get("sec-fetch-site") or "").strip().lower()
            origin = (request.headers.get("origin") or "").strip()
            referer_origin = _origin_da_referer((request.headers.get("referer") or "").strip())
            effective_origin = origin or referer_origin
            host = (request.headers.get("host") or "").strip().lower()
            is_testclient = (not _IS_WORKER) and host == "testserver"

            if sec_fetch_site == "cross-site":
                return Response(
                    content=json.dumps({"detail": "Richiesta cross-site non consentita."}),
                    status_code=403,
                    media_type="application/json",
                )
            if effective_origin and effective_origin not in ALLOWED_ORIGINS_SET:
                return Response(
                    content=json.dumps({"detail": "Origine richiesta non consentita."}),
                    status_code=403,
                    media_type="application/json",
                )
            if not is_testclient and not effective_origin and sec_fetch_site not in ("same-origin", "same-site"):
                return Response(
                    content=json.dumps({"detail": "Header di origine mancante per richiesta autenticata."}),
                    status_code=403,
                    media_type="application/json",
                )

    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

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
