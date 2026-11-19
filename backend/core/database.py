"""Connessione a Cloudflare D1 e utilities per le query SQL preparate."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from fastapi import HTTPException, Request


@dataclass
class CloudflareServices:
    database: Any
    uploads: Any


class D1Store:
    def __init__(self, binding: Any):
        self.binding = binding

    async def all(self, query: str, *parameters: Any) -> list[dict[str, Any]]:
        statement = self.binding.prepare(query)
        if parameters:
            statement = statement.bind(*parameters)
        result = await statement.all()
        return list(result.results)

    async def one(self, query: str, *parameters: Any) -> Optional[dict[str, Any]]:
        rows = await self.all(query, *parameters)
        return rows[0] if rows else None

    async def run(self, query: str, *parameters: Any) -> Any:
        statement = self.binding.prepare(query)
        if parameters:
            statement = statement.bind(*parameters)
        return await statement.run()


def get_environment(request: Request) -> Any:
    environment = request.scope.get("env")
    if environment is None:
        environment = getattr(request.app.state, "env", None)
    if environment is None:
        raise HTTPException(
            status_code=503,
            detail="Binding Cloudflare non disponibile per questa richiesta.",
        )
    return environment


def get_services(request: Request) -> CloudflareServices:
    environment = get_environment(request)
    try:
        return CloudflareServices(
            database=environment.DB,
            uploads=environment.UPLOADS,
        )
    except AttributeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Binding DB o UPLOADS non configurati correttamente nell'ambiente.",
        ) from exc


def valore_data_iso(valore: Any) -> Optional[str]:
    if valore is None:
        return None
    if isinstance(valore, datetime):
        return valore.isoformat()
    return str(valore).replace(" ", "T", 1)
