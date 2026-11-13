import { env } from 'cloudflare:workers';
import { defineMiddleware } from 'astro:middleware';

export const onRequest = defineMiddleware(async ({ request, url }, next) => {
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

  // Content-Security-Policy (CSP)
  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self'",
    "connect-src 'self' https:",
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
