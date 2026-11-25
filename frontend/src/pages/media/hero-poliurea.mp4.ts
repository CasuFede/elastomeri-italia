import type { APIRoute } from 'astro';
import { env } from 'cloudflare:workers';

export const prerender = false;

async function handleVideoRequest(request: Request, url: URL): Promise<Response> {
  const sourceUrl = new URL('/videos/hero-poliurea.mp4', url.origin).toString();
  const assets = (env as unknown as { ASSETS?: { fetch: (req: Request | string) => Promise<Response> } })?.ASSETS;

  const assetRes =
    assets && typeof assets.fetch === 'function'
      ? await assets.fetch(new Request(sourceUrl, { method: 'GET' }))
      : await fetch(new Request(sourceUrl, { method: 'GET' }));

  if (!assetRes.ok) {
    return new Response('Video non trovato', { status: assetRes.status });
  }

  const contentType = assetRes.headers.get('content-type') || 'video/mp4';
  const etag = assetRes.headers.get('etag');
  const rangeHeader = request.headers.get('range');
  const isHead = request.method === 'HEAD';

  const makeHeaders = (extra: Record<string, string>) => {
    const h = new Headers({
      'Content-Type': contentType,
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'public, max-age=31536000, immutable',
      'X-Content-Type-Options': 'nosniff',
      ...extra,
    });
    if (etag) h.set('ETag', etag);
    return h;
  };

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

export const GET: APIRoute = ({ request, url }) => handleVideoRequest(request, url);
export const HEAD: APIRoute = ({ request, url }) => handleVideoRequest(request, url);
