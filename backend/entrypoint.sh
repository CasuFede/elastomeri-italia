#!/bin/sh
set -e

echo "[ENTRYPOINT] Avvio SMTP Bridge per Aruba SMTPS su porta 8025..."
uv run python /app/smtp_bridge.py &

echo "[ENTRYPOINT] Avvio Pywrangler per API Worker..."
exec uv run pywrangler dev --ip 0.0.0.0 --port 8000
