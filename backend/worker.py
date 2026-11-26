import re
from urllib.parse import urlparse

from js import Object
from pyodide.ffi import to_js
from workers import Response, WorkerEntrypoint, asgi

from main import app

_MEDIA_PATH_RE = re.compile(r"^/(?:api/)?lavori/(\d+)/media/(\d+)(/poster)?$")
_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$", re.IGNORECASE)


async def _stream_lavoro_media(request, env, lavoro_id: int, media_id: int, is_poster: bool):
    """Streaming zero-copy da R2 (Web ReadableStream) con supporto RFC 9110 Range 206."""
    is_head = str(request.method).upper() == "HEAD"

    if is_poster:
        stmt = env.DB.prepare(
            "SELECT poster_file AS nome_file, poster_mime AS tipo_mime "
            "FROM lavori_media WHERE id = ? AND lavoro_id = ? LIMIT 1"
        ).bind(media_id, lavoro_id)
    else:
        stmt = env.DB.prepare(
            "SELECT nome_file, tipo_mime "
            "FROM lavori_media WHERE id = ? AND lavoro_id = ? LIMIT 1"
        ).bind(media_id, lavoro_id)

    res = await stmt.all()
    rows = list(res.results)
    if not rows:
        return Response("Media non trovato.", status=404)

    row = rows[0].to_py() if hasattr(rows[0], "to_py") else rows[0]
    nome_file = str((row.get("nome_file") if isinstance(row, dict) else getattr(row, "nome_file", "")) or "").strip()
    tipo_mime = str((row.get("tipo_mime") if isinstance(row, dict) else getattr(row, "tipo_mime", "")) or "").strip()
    if not nome_file:
        return Response("Media non disponibile.", status=404)
    if not tipo_mime:
        tipo_mime = "image/jpeg" if is_poster else "application/octet-stream"

    key = f"lavori/{lavoro_id}/{nome_file}"
    base_headers = {
        "Content-Type": tipo_mime,
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=31536000, immutable",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }

    range_header = request.headers.get("range")
    if not range_header:
        if is_head:
            head = await env.UPLOADS.head(key)
            if not head:
                return Response("File non disponibile.", status=404)
            headers = {**base_headers, "Content-Length": str(int(head.size))}
            return Response(None, status=200, headers=headers)
        obj = await env.UPLOADS.get(key)
        if not obj:
            return Response("File non disponibile.", status=404)
        headers = {**base_headers, "Content-Length": str(int(obj.size))}
        return Response(obj.body, status=200, headers=headers)

    head = await env.UPLOADS.head(key)
    if not head:
        return Response("File non disponibile.", status=404)
    total = int(head.size)

    match = _RANGE_RE.match(str(range_header).strip())
    if not match or (match.group(1) == "" and match.group(2) == ""):
        return Response(
            None,
            status=416,
            headers={**base_headers, "Content-Range": f"bytes */{total}"},
        )

    start_str, end_str = match.group(1), match.group(2)
    if start_str == "":
        suffix = int(end_str)
        if suffix <= 0:
            return Response(
                None,
                status=416,
                headers={**base_headers, "Content-Range": f"bytes */{total}"},
            )
        start = max(0, total - suffix)
        end = total - 1
    else:
        start = int(start_str)
        end = total - 1 if end_str == "" else min(int(end_str), total - 1)

    if start < 0 or start >= total or start > end:
        return Response(
            None,
            status=416,
            headers={**base_headers, "Content-Range": f"bytes */{total}"},
        )

    length = end - start + 1
    range_headers = {
        **base_headers,
        "Content-Range": f"bytes {start}-{end}/{total}",
        "Content-Length": str(length),
    }

    if is_head:
        return Response(None, status=206, headers=range_headers)

    opts = to_js(
        {"range": {"offset": start, "length": length}},
        dict_converter=Object.fromEntries,
    )
    obj = await env.UPLOADS.get(key, opts)
    if not obj:
        return Response("File non disponibile.", status=404)
    return Response(obj.body, status=206, headers=range_headers)


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        method = str(request.method).upper()
        if method in ("GET", "HEAD"):
            path = urlparse(str(request.url)).path
            m = _MEDIA_PATH_RE.match(path)
            if m:
                return await _stream_lavoro_media(
                    request,
                    self.env,
                    int(m.group(1)),
                    int(m.group(2)),
                    bool(m.group(3)),
                )
        return await asgi.fetch(app, request.js_object, self.env)
