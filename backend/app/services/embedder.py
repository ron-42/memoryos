import hashlib

from app.core.config import get_settings

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - optional at runtime
    AsyncOpenAI = None


EMBEDDING_DIMENSION = 1536


class EmbedderService:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key and AsyncOpenAI else None

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self.client and texts:
            response = await self.client.embeddings.create(model="text-embedding-3-small", input=texts)
            return [item.embedding for item in response.data]
        return [self._fallback_embedding(text) for text in texts]

    async def embed_query(self, query: str) -> list[float]:
        embeddings = await self.embed_texts([query])
        return embeddings[0]

    def _fallback_embedding(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        while len(values) < EMBEDDING_DIMENSION:
            for byte in digest:
                values.append(round((byte / 127.5) - 1.0, 6))
                if len(values) == EMBEDDING_DIMENSION:
                    break
            digest = hashlib.sha256(digest + text.encode("utf-8")).digest()
        return values
