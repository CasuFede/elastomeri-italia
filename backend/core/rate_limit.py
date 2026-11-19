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
