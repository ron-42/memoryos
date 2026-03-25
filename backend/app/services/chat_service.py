import asyncio
from collections.abc import AsyncGenerator
import logging

from app.core.config import get_settings
from app.models.chat import ChatCitation, ChatCompletedEvent
from app.services.retriever import RetrieverService

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - optional at runtime
    genai = None

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, retriever: RetrieverService | None = None) -> None:
        self.retriever = retriever or RetrieverService()
        self.settings = get_settings()

    async def stream_chat(self, query: str, user_id) -> AsyncGenerator[str, None]:
        yield self._sse({"type": "progress", "stage": "retrieving", "message": "Searching your memories"})
        retrieval_items = await self.retriever.retrieve(query=query, user_id=user_id, top_k=5)

        citations = [
            ChatCitation(
                memory_id=str(item.memory_id),
                title=item.title,
                source_url=item.source_url,
                similarity=item.similarity,
                excerpt=item.chunk_text[:280],
            )
            for item in retrieval_items
        ]

        if not retrieval_items:
            answer = "I could not find relevant memories for that question yet."
        else:
            answer = await self._generate_answer(query=query, citations=citations)

        yield self._sse({"type": "progress", "stage": "responding", "message": "Streaming grounded answer"})
        for piece in self._chunk_text(answer):
            yield self._sse({"type": "chunk", "content": piece})
            await asyncio.sleep(0)

        yield self._sse(ChatCompletedEvent(answer=answer, citations=citations).model_dump())

    async def _generate_answer(self, query: str, citations: list[ChatCitation]) -> str:
        if self.settings.gemini_api_key and genai is not None and citations:
            try:
                return await asyncio.to_thread(self._generate_with_gemini, query, citations)
            except Exception:
                logger.exception("gemini answer generation failed")
        return self._fallback_answer(query, citations)

    def _generate_with_gemini(self, query: str, citations: list[ChatCitation]) -> str:
        genai.configure(api_key=self.settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        context = "\n\n".join(
            f"Memory {index + 1}: {citation.title or 'Untitled'}\nSource: {citation.source_url or 'n/a'}\nExcerpt: {citation.excerpt}"
            for index, citation in enumerate(citations)
        )
        prompt = f"""
You are the user's memory. Answer only from the provided memory context.
If the memory context is partial, say so directly.
Keep the response concise and grounded.

User question: {query}

Memory context:
{context}
""".strip()
        response = model.generate_content(prompt)
        return response.text.strip()

    def _fallback_answer(self, query: str, citations: list[ChatCitation]) -> str:
        if not citations:
            return "I do not have enough stored context to answer that from your memories."
        lines = [f"Based on your stored memories, here is what stands out about '{query}':"]
        for citation in citations[:3]:
            label = citation.title or "Untitled memory"
            lines.append(f"- {label}: {citation.excerpt}")
        lines.append("This answer is grounded only in the retrieved captures above.")
        return "\n".join(lines)

    def _chunk_text(self, text: str, chunk_size: int = 120) -> list[str]:
        return [text[index:index + chunk_size] for index in range(0, len(text), chunk_size)] or [text]

    def _sse(self, payload: dict) -> str:
        import json

        return f"data: {json.dumps(payload)}\n\n"
