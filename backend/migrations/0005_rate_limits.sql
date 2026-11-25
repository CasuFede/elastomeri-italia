-- Migration 0005: Tabella persistente per rate limiting distribuito su Cloudflare D1
CREATE TABLE IF NOT EXISTS rate_limits (
    k TEXT PRIMARY KEY,
    count INTEGER NOT NULL,
    window_start INTEGER NOT NULL
);
