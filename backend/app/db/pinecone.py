from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_API_VERSION = "2025-04"


class PineconeIndexClient:
    def __init__(self, api_key: str, index_host: str, namespace: str) -> None:
        base_url = index_host if index_host.startswith("http") else f"https://{index_host}"
        self.namespace = namespace or "__default__"
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=30.0,
            headers={
                "Api-Key": api_key,
                "X-Pinecone-Api-Version": _API_VERSION,
                "Content-Type": "application/json",
            },
        )

    async def upsert(self, vectors: list[dict[str, Any]]) -> int:
        response = await self._http.post(
            "/vectors/upsert",
            json={
                "vectors": vectors,
                "namespace": self.namespace,
            },
        )
        self._raise_for_status(response, operation="vectors.upsert")
        payload = response.json()
        return int(payload.get("upsertedCount") or 0)

    async def query(
        self,
        vector: list[float],
        top_k: int,
        filter: dict[str, Any] | None = None,
        include_metadata: bool = True,
        include_values: bool = False,
    ) -> list[dict[str, Any]]:
        response = await self._http.post(
            "/query",
            json={
                "namespace": self.namespace,
                "vector": vector,
                "topK": top_k,
                "filter": filter or {},
                "includeMetadata": include_metadata,
                "includeValues": include_values,
            },
        )
        self._raise_for_status(response, operation="query")
        payload = response.json()
        return list(payload.get("matches") or [])

    async def aclose(self) -> None:
        await self._http.aclose()

    def _raise_for_status(self, response: httpx.Response, operation: str) -> None:
        if response.is_success:
            return
        logger.error(
            "pinecone request failed operation=%s status=%s url=%s body=%s",
            operation,
            response.status_code,
            response.request.url,
            response.text[:800],
        )
        response.raise_for_status()


async def get_pinecone_client() -> PineconeIndexClient | None:
    settings = get_settings()
    if not settings.pinecone_api_key or not settings.pinecone_index_host:
        logger.warning("pinecone is not configured; dense vector operations will be skipped")
        return None
    return PineconeIndexClient(
        api_key=settings.pinecone_api_key,
        index_host=settings.pinecone_index_host,
        namespace=settings.pinecone_namespace,
    )
