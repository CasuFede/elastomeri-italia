import type { APIRoute } from 'astro';
import { env } from 'cloudflare:workers';

export const prerender = false;

const SAFE_VIDEO_NAME = /^[a-z0-9][a-z0-9._-]{0,120}\.(mp4|webm)$/i;

async function handleVideoRequest(request: Request, url: URL, fileParam: string | undefined): Promise<Response> {
  if (!fileParam || !SAFE_VIDEO_NAME.test(fileParam) || fileParam.includes('..')) {
    return new Response('Video non valido', { status: 400 });
  }

  const sourceUrl = new URL(`/videos/${fileParam}`, url.origin).toString();
  const assets = (env as unknown as { ASSETS?: { fetch: (req: Request | string) => Promise<Response> } })?.ASSETS;
  const rangeHeader = request.headers.get('range');
  const isHead = request.method === 'HEAD';
  const isHttps = url.protocol === 'https:' || request.headers.get('x-forwarded-proto') === 'https';

  // Usiamo sempre GET verso ASSETS perché ASSETS.fetch su HEAD può omettere Content-Length e Range
  const forwardHeaders = new Headers();
  if (rangeHeader) {
    forwardHeaders.set('Range', rangeHeader);
  } else if (isHead) {
    forwardHeaders.set('Range', 'bytes=0-0');
  }
  const upstreamReq = new Request(sourceUrl, {
    method: 'GET',
    headers: forwardHeaders,
  });

  const assetRes =
    assets && typeof assets.fetch === 'function'
      ? await assets.fetch(upstreamReq)
      : await fetch(upstreamReq);

  if (!assetRes.ok && assetRes.status !== 206) {
    return new Response('Video non trovato', { status: assetRes.status });
  }

  const fallbackType = fileParam.toLowerCase().endsWith('.webm') ? 'video/webm' : 'video/mp4';
  const contentType = assetRes.headers.get('content-type') || fallbackType;
  const etag = assetRes.headers.get('etag');

  const makeHeaders = (extra: Record<string, string>) => {
    const h = new Headers({
      'Content-Type': contentType,
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'public, max-age=31536000, immutable',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      ...extra,
    });
    if (isHttps) {
      h.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
    }
    if (etag) h.set('ETag', etag);
    return h;
  };

  // Percorso zero-copy: se ASSETS supporta nativamente 206 Partial Content, passa lo stream senza arrayBuffer()
  if (assetRes.status === 206) {
    const contentRange = assetRes.headers.get('content-range');
    const contentLength = assetRes.headers.get('content-length');
    if (isHead && !rangeHeader) {
      if (assetRes.body) await assetRes.body.cancel();
      const totalFromRange = contentRange?.match(/\/(\d+)$/)?.[1];
      return new Response(null, {
        status: 200,
        headers: makeHeaders(totalFromRange ? { 'Content-Length': totalFromRange } : {}),
      });
    }
    const extra: Record<string, string> = {};
    if (contentRange) extra['Content-Range'] = contentRange;
    if (contentLength) extra['Content-Length'] = contentLength;
    if (isHead && assetRes.body) await assetRes.body.cancel();
    return new Response(isHead ? null : assetRes.body, {
      status: 206,
      headers: makeHeaders(extra),
    });
  }

  const declaredSize = Number(assetRes.headers.get('content-length') || '0');

  if (!rangeHeader) {
    if (isHead) {
      let total = declaredSize;
      if (!total) {
        const buf = await assetRes.arrayBuffer();
        total = buf.byteLength;
      } else if (assetRes.body) {
        await assetRes.body.cancel();
      }
      return new Response(null, {
        status: 200,
        headers: makeHeaders({ 'Content-Length': String(total) }),
      });
    }
    return new Response(assetRes.body, {
      status: 200,
      headers: makeHeaders(declaredSize ? { 'Content-Length': String(declaredSize) } : {}),
    });
  }

  const fileBuffer = await assetRes.arrayBuffer();
  const total = fileBuffer.byteLength;
  const match = /^bytes=(\d*)-(\d*)$/i.exec(rangeHeader.trim());

  if (!match || (match[1] === '' && match[2] === '')) {
    return new Response(null, {
      status: 416,
      headers: makeHeaders({ 'Content-Range': `bytes */${total}` }),
    });
  }

  let start: number;
  let end: number;

  if (match[1] === '') {
    const suffix = Number(match[2]);
    if (!Number.isFinite(suffix) || suffix <= 0) {
      return new Response(null, {
        status: 416,
        headers: makeHeaders({ 'Content-Range': `bytes */${total}` }),
      });
    }
    start = Math.max(0, total - suffix);
    end = total - 1;
  } else {
    start = Number(match[1]);
    end = match[2] === '' ? total - 1 : Math.min(Number(match[2]), total - 1);
  }

  if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || start >= total || start > end) {
    return new Response(null, {
      status: 416,
      headers: makeHeaders({ 'Content-Range': `bytes */${total}` }),
    });
  }

  const chunkLength = end - start + 1;
  const body = isHead ? null : fileBuffer.slice(start, end + 1);

  return new Response(body, {
    status: 206,
    headers: makeHeaders({
      'Content-Range': `bytes ${start}-${end}/${total}`,
      'Content-Length': String(chunkLength),
    }),
  });
}

export const GET: APIRoute = ({ request, url, params }) => handleVideoRequest(request, url, params.file);
export const HEAD: APIRoute = ({ request, url, params }) => handleVideoRequest(request, url, params.file);
