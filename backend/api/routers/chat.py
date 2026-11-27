"""Router per chat informativa tecnica basata su knowledge base."""
from fastapi import APIRouter, HTTPException, Request

from chat_knowledge import rispondi
from core.database import D1Store, get_services
from core.rate_limit import check_rate_limit_d1, get_client_ip
from schemas.chat import ChatRequest

router = APIRouter(tags=["Chatbot"])


def _store_chat_opzionale(request: Request) -> D1Store | None:
    try:
        services = get_services(request)
        if services.database is not None:
            return D1Store(services.database)
    except Exception:
        pass
    return None


@router.post("/chat")
async def chat_informativa(dati: ChatRequest, request: Request):
    ip = get_client_ip(request)
    store = _store_chat_opzionale(request)
    if not await check_rate_limit_d1(store, "chat", ip, max_requests=30, window_seconds=60):
        raise HTTPException(
            status_code=429,
            detail="Stai inviando troppi messaggi in poco tempo. Attendi qualche istante prima di continuare.",
        )
    messaggi = dati.messages
    if (
        messaggi[0].role != "user"
        or messaggi[-1].role != "user"
        or any(not messaggio.content.strip() for messaggio in messaggi)
        or any(
            precedente.role == corrente.role
            for precedente, corrente in zip(messaggi, messaggi[1:])
        )
    ):
        raise HTTPException(
            status_code=422,
            detail="La conversazione non è valida. Ricarica la pagina e riprova.",
        )

    contesto = next(
        (
            messaggio.content.strip()
            for messaggio in reversed(messaggi[:-1])
            if messaggio.role == "user"
        ),
        "",
    )
    return {
        "answer": rispondi(
            messaggi[-1].content.strip(),
            contesto=contesto,
        )
    }
