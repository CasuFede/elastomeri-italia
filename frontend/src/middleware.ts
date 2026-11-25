import { env } from 'cloudflare:workers';
import { defineMiddleware } from 'astro:middleware';

export const onRequest = defineMiddleware(async ({ request, url }, next) => {
  // Pass-through diretto per endpoint media (mantiene intatti 206 Partial Content / Content-Range)
  if (url.pathname.startsWith('/media/')) {
    return next();
  }

  // Canonicalizzazione URL: redirect 301 da /percorso/ a /percorso (evita pagine duplicate SEO)
  if (
    (request.method === 'GET' || request.method === 'HEAD') &&
    url.pathname.length > 1 &&
    url.pathname.endsWith('/') &&
    !url.pathname.startsWith('/api/')
  ) {
    const cleanUrl = new URL(url.toString());
    cleanUrl.pathname = url.pathname.replace(/\/+$/, '');
    return Response.redirect(cleanUrl.toString(), 301);
  }

  // Protezione SSR preventiva per rotte riservate: verifica reale del token HMAC lato API
  if (url.pathname === '/admin' || url.pathname.startsWith('/admin/')) {
    const cookieHeader = request.headers.get('cookie') || '';
    if (!cookieHeader.includes('poliurea_admin_session=')) {
      return Response.redirect(new URL('/accesso-preventivi', url).toString(), 302);
    }
    const api = (env as unknown as { API?: { fetch: (req: Request) => Promise<Response> } })?.API;
    if (api && typeof api.fetch === 'function') {
      try {
        const authRes = await api.fetch(
          new Request(new URL('/api/auth/admin/me', url).toString(), {
            method: 'GET',
            headers: { cookie: cookieHeader },
          })
        );
        if (authRes.status !== 200) {
          return Response.redirect(new URL('/accesso-preventivi', url).toString(), 302);
        }
      } catch {
        return Response.redirect(new URL('/accesso-preventivi', url).toString(), 302);
      }
    }
  }

  let response: Response;

  if (url.pathname === '/api' || url.pathname.startsWith('/api/')) {
    response = await env.API.fetch(new Request(request));
  } else {
    response = await next();
  }

  const headers = new Headers(response.headers);

  // Security Headers
  headers.set('X-Frame-Options', 'DENY');
  headers.set('X-Content-Type-Options', 'nosniff');
  headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');

  // Content-Security-Policy (CSP) restrittiva: solo risorse first-party
  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "media-src 'self' blob:",
    "font-src 'self'",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; ');
  headers.set('Content-Security-Policy', csp);

  // Strict-Transport-Security (HSTS) se in HTTPS
  const isHttps = url.protocol === 'https:' || request.headers.get('x-forwarded-proto') === 'https';
  if (isHttps) {
    headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
  }

  const body = [204, 205, 304].includes(response.status) ? null : response.body;

  return new Response(body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
});
