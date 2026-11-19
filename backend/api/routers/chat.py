"""Router per chat informativa tecnica basata su knowledge base."""
from fastapi import APIRouter, HTTPException, Request

from chat_knowledge import rispondi
from core.rate_limit import get_client_ip, rate_limiter
from schemas.chat import ChatRequest

router = APIRouter(tags=["Chatbot"])


@router.post("/chat")
async def chat_informativa(dati: ChatRequest, request: Request):
    ip = get_client_ip(request)
    if not rate_limiter.check("chat", ip, max_requests=30, window_seconds=60):
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
