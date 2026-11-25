"""Gestione del rate limiting e rilevamento sicuro dell'IP client."""
import time
from collections import defaultdict
from typing import Any
from fastapi import Request


class InMemoryRateLimiter:
    def __init__(self):
        self._hits: dict[str, list[float]] = defaultdict(list)

    def prune_if_needed(self):
        if len(self._hits) > 1000:
            now = time.time()
            keys_to_delete = [
                k for k, v in self._hits.items()
                if not v or now - v[-1] > 1800
            ]
            for k in keys_to_delete:
                del self._hits[k]

    def check(self, bucket: str, ip: str, max_requests: int, window_seconds: int) -> bool:
        self.prune_if_needed()
        now = time.time()
        key = f"{bucket}:{ip}"
        cutoff = now - window_seconds
        timestamps = [t for t in self._hits[key] if t > cutoff]
        if len(timestamps) >= max_requests:
            self._hits[key] = timestamps
            return False
        timestamps.append(now)
        self._hits[key] = timestamps
        return True

    def record_failure(self, bucket: str, ip: str):
        self.prune_if_needed()
        now = time.time()
        key = f"{bucket}:{ip}"
        self._hits[key].append(now)

    def is_blocked(self, bucket: str, ip: str, max_failures: int, window_seconds: int) -> bool:
        now = time.time()
        key = f"{bucket}:{ip}"
        cutoff = now - window_seconds
        failures = [t for t in self._hits[key] if t > cutoff]
        self._hits[key] = failures
        return len(failures) >= max_failures

    def reset(self, bucket: str, ip: str):
        key = f"{bucket}:{ip}"
        self._hits.pop(key, None)


rate_limiter = InMemoryRateLimiter()
_D1_TABLE_READY = False


async def _ensure_rate_limit_table(store: Any) -> None:
    global _D1_TABLE_READY
    if _D1_TABLE_READY:
        return
    await store.run(
        "CREATE TABLE IF NOT EXISTS rate_limits ("
        "k TEXT PRIMARY KEY, "
        "count INTEGER NOT NULL, "
        "window_start INTEGER NOT NULL)"
    )
    _D1_TABLE_READY = True


async def check_rate_limit_d1(
    store: Any, bucket: str, ip: str, max_requests: int, window_seconds: int
) -> bool:
    """Rate limiter persistente su Cloudflare D1 con fallback in memoria."""
    if not rate_limiter.check(bucket, ip, max_requests, window_seconds):
        return False
    if store is None:
        return True
    try:
        await _ensure_rate_limit_table(store)
        now = int(time.time())
        key = f"{bucket}:{ip}"
        row = await store.one(
            "SELECT count, window_start FROM rate_limits WHERE k = ? LIMIT 1", key
        )
        if row and (now - int(row["window_start"])) < window_seconds:
            if int(row["count"]) >= max_requests:
                return False
            await store.run(
                "UPDATE rate_limits SET count = count + 1 WHERE k = ?", key
            )
        else:
            await store.run(
                "INSERT INTO rate_limits (k, count, window_start) VALUES (?, 1, ?) "
                "ON CONFLICT(k) DO UPDATE SET count = 1, window_start = excluded.window_start",
                key,
                now,
            )
    except Exception:
        pass
    return True


async def is_blocked_d1(
    store: Any, bucket: str, ip: str, max_failures: int, window_seconds: int
) -> bool:
    """Verifica se l'IP è bloccato per troppi tentativi falliti (D1 + memoria)."""
    if rate_limiter.is_blocked(bucket, ip, max_failures, window_seconds):
        return True
    if store is None:
        return False
    try:
        await _ensure_rate_limit_table(store)
        now = int(time.time())
        key = f"fail:{bucket}:{ip}"
        row = await store.one(
            "SELECT count, window_start FROM rate_limits WHERE k = ? LIMIT 1", key
        )
        if row and (now - int(row["window_start"])) < window_seconds:
            return int(row["count"]) >= max_failures
    except Exception:
        pass
    return False


async def record_failure_d1(store: Any, bucket: str, ip: str, window_seconds: int) -> None:
    """Registra un tentativo fallito su memoria e Cloudflare D1."""
    rate_limiter.record_failure(bucket, ip)
    if store is None:
        return
    try:
        await _ensure_rate_limit_table(store)
        now = int(time.time())
        key = f"fail:{bucket}:{ip}"
        row = await store.one(
            "SELECT count, window_start FROM rate_limits WHERE k = ? LIMIT 1", key
        )
        if row and (now - int(row["window_start"])) < window_seconds:
            await store.run("UPDATE rate_limits SET count = count + 1 WHERE k = ?", key)
        else:
            await store.run(
                "INSERT INTO rate_limits (k, count, window_start) VALUES (?, 1, ?) "
                "ON CONFLICT(k) DO UPDATE SET count = 1, window_start = excluded.window_start",
                key,
                now,
            )
    except Exception:
        pass


async def reset_failures_d1(store: Any, bucket: str, ip: str) -> None:
    """Azzera i fallimenti per IP dopo autenticazione riuscita."""
    rate_limiter.reset(bucket, ip)
    if store is None:
        return
    try:
        await _ensure_rate_limit_table(store)
        await store.run("DELETE FROM rate_limits WHERE k = ?", f"fail:{bucket}:{ip}")
    except Exception:
        pass


def get_client_ip(request: Request) -> str:
    # 1. Cloudflare Edge IP (priorità massima e autenticato dai server Cloudflare)
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()

    # 2. X-Real-IP impostato in modo immutabile dal reverse proxy Nginx fidato ($remote_addr)
    x_real = request.headers.get("x-real-ip")
    if x_real and x_real.strip():
        return x_real.strip()

    # 3. Socket peer IP diretto
    if request.client and request.client.host:
        return request.client.host.strip()

    # 4. Fallback controllato su X-Forwarded-For (prende l'ultimo hop accodato dal proxy)
    x_forwarded = request.headers.get("x-forwarded-for")
    if x_forwarded and x_forwarded.strip():
        parti = [p.strip() for p in x_forwarded.split(",") if p.strip()]
        if parti:
            return parti[-1]

    return "127.0.0.1"
