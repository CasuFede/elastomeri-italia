"""Operazioni di storage su bucket Cloudflare R2 e validazione file."""
import re
from typing import Any, Optional
from fastapi import HTTPException, Response

MAX_RANGE_CHUNK = 1 * 1024 * 1024  # 1 MB max per singola risposta 206 in fallback FastAPI
_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$", re.IGNORECASE)


def tipo_immagine(contenuto: bytes) -> Optional[tuple[str, str]]:
    if contenuto.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if contenuto.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if len(contenuto) >= 12 and contenuto[:4] == b"RIFF" and contenuto[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


def tipo_video(contenuto: bytes) -> Optional[tuple[str, str]]:
    """Valida video MP4/MOV (ISO BMFF ftyp box) o WEBM (EBML) tramite magic bytes."""
    if len(contenuto) >= 12 and contenuto[4:8] == b"ftyp":
        return "video/mp4", ".mp4"
    if contenuto.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm", ".webm"
    return None


async def salva_su_r2(bucket: Any, key: str, contenuto: bytes) -> None:
    await bucket.put(key, contenuto)


async def elimina_da_r2(bucket: Any, key: str) -> None:
    if not key:
        return
    await bucket.delete(key)


async def _leggi_oggetto_bytes(oggetto: Any) -> Optional[bytes]:
    if oggetto is None:
        return None
    try:
        from js import Uint8Array
        contenuto = await oggetto.arrayBuffer()
        return bytes(Uint8Array.new(contenuto).to_py())
    except ImportError:
        if isinstance(oggetto, (bytes, bytearray)):
            return bytes(oggetto)
        if hasattr(oggetto, "read"):
            return await oggetto.read()
        return None


async def leggi_da_r2(bucket: Any, key: str) -> Optional[bytes]:
    oggetto = await bucket.get(key)
    return await _leggi_oggetto_bytes(oggetto)


async def _leggi_range_da_r2(
    bucket: Any, key: str, start: int, length: int
) -> Optional[bytes]:
    try:
        from js import Object
        from pyodide.ffi import to_js

        opts = to_js(
            {"range": {"offset": start, "length": length}},
            dict_converter=Object.fromEntries,
        )
        oggetto = await bucket.get(key, opts)
        return await _leggi_oggetto_bytes(oggetto)
    except ImportError:
        full = await leggi_da_r2(bucket, key)
        if full is None:
            return None
        return full[start : start + length]


async def risposta_file(bucket: Any, key: str, tipo_mime: str) -> Response:
    contenuto = await leggi_da_r2(bucket, key)
    if contenuto is None:
        raise HTTPException(status_code=404, detail="File non disponibile.")
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Accept-Ranges": "bytes",
        "Cache-Control": (
            "public, max-age=86400, immutable"
            if key.startswith("lavori/")
            else "private, no-cache"
        ),
    }
    return Response(content=contenuto, media_type=tipo_mime, headers=headers)


async def risposta_media_range(
    bucket: Any,
    key: str,
    tipo_mime: str,
    range_header: Optional[str] = None,
) -> Response:
    """Restituisce un media da R2 con supporto RFC 9110 206 Partial Content per streaming video/iOS."""
    cache_control = (
        "public, max-age=31536000, immutable"
        if key.startswith("lavori/")
        else "private, no-cache"
    )
    base_headers = {
        "X-Content-Type-Options": "nosniff",
        "Accept-Ranges": "bytes",
        "Cache-Control": cache_control,
    }

    if not range_header:
        contenuto = await leggi_da_r2(bucket, key)
        if contenuto is None:
            raise HTTPException(status_code=404, detail="File non disponibile.")
        headers = {**base_headers, "Content-Length": str(len(contenuto))}
        return Response(content=contenuto, media_type=tipo_mime, headers=headers)

    # Determina dimensione totale tramite R2 head (evita di caricare tutto il video in RAM)
    total: Optional[int] = None
    if hasattr(bucket, "head"):
        meta = await bucket.head(key)
        if meta is None:
            raise HTTPException(status_code=404, detail="File non disponibile.")
        size_val = getattr(meta, "size", None)
        if size_val is not None:
            total = int(size_val)

    full_fallback: Optional[bytes] = None
    if total is None:
        full_fallback = await leggi_da_r2(bucket, key)
        if full_fallback is None:
            raise HTTPException(status_code=404, detail="File non disponibile.")
        total = len(full_fallback)

    match = _RANGE_RE.match(range_header.strip())
    if not match or (match.group(1) == "" and match.group(2) == ""):
        return Response(
            content=b"",
            status_code=416,
            headers={**base_headers, "Content-Range": f"bytes */{total}"},
        )

    start_str, end_str = match.group(1), match.group(2)
    if start_str == "":
        suffix = int(end_str)
        if suffix <= 0:
            return Response(
                content=b"",
                status_code=416,
                headers={**base_headers, "Content-Range": f"bytes */{total}"},
            )
        start = max(0, total - suffix)
        end = total - 1
    else:
        start = int(start_str)
        end = total - 1 if end_str == "" else min(int(end_str), total - 1)

    if start < 0 or start >= total or start > end:
        return Response(
            content=b"",
            status_code=416,
            headers={**base_headers, "Content-Range": f"bytes */{total}"},
        )

    # Limita il singolo chunk 206 per proteggere la memoria del Worker su video grandi
    if end - start + 1 > MAX_RANGE_CHUNK:
        end = start + MAX_RANGE_CHUNK - 1

    chunk_len = end - start + 1
    if full_fallback is not None:
        chunk = full_fallback[start : end + 1]
    else:
        chunk = await _leggi_range_da_r2(bucket, key, start, chunk_len)
        if chunk is None:
            raise HTTPException(status_code=404, detail="File non disponibile.")

    headers = {
        **base_headers,
        "Content-Range": f"bytes {start}-{start + len(chunk) - 1}/{total}",
        "Content-Length": str(len(chunk)),
    }
    return Response(content=chunk, status_code=206, media_type=tipo_mime, headers=headers)
