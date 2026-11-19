"""Operazioni di storage su bucket Cloudflare R2 e validazione file."""
from typing import Any, Optional
from fastapi import HTTPException, Response


def tipo_immagine(contenuto: bytes) -> Optional[tuple[str, str]]:
    if contenuto.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if contenuto.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if len(contenuto) >= 12 and contenuto[:4] == b"RIFF" and contenuto[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


async def salva_su_r2(bucket: Any, key: str, contenuto: bytes) -> None:
    await bucket.put(key, contenuto)


async def elimina_da_r2(bucket: Any, key: str) -> None:
    await bucket.delete(key)


async def leggi_da_r2(bucket: Any, key: str) -> Optional[bytes]:
    oggetto = await bucket.get(key)
    if oggetto is None:
        return None
    try:
        from js import Uint8Array
        contenuto = await oggetto.arrayBuffer()
        return bytes(Uint8Array.new(contenuto).to_py())
    except ImportError:
        # Fallback per test fuori da Pyodide se oggetto ha metodi standard
        if hasattr(oggetto, "read"):
            return await oggetto.read()
        return None


async def risposta_file(bucket: Any, key: str, tipo_mime: str) -> Response:
    contenuto = await leggi_da_r2(bucket, key)
    if contenuto is None:
        raise HTTPException(status_code=404, detail="File non disponibile.")
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": (
            "public, max-age=86400, immutable"
            if key.startswith("lavori/")
            else "private, no-cache"
        ),
    }
    return Response(content=contenuto, media_type=tipo_mime, headers=headers)
