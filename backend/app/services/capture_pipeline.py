from collections.abc import AsyncGenerator
import logging

from app.core.security import UserContext
from app.models.capture import CaptureStreamEvent, CapturedContent, EnrichmentPayload
from app.services.chunker import ChunkerService
from app.services.connections import ConnectionService
from app.services.embedder import EmbedderService
from app.services.enrichment import EnrichmentService
from app.services.fetcher import FetcherService
from app.services.repository import MemoryRepository, RepositoryCapturePayload

logger = logging.getLogger(__name__)


class CapturePipelineService:
    def __init__(
        self,
        fetcher: FetcherService | None = None,
        enrichment: EnrichmentService | None = None,
        chunker: ChunkerService | None = None,
        embedder: EmbedderService | None = None,
        repository: MemoryRepository | None = None,
        connections: ConnectionService | None = None,
    ) -> None:
        self.fetcher = fetcher or FetcherService()
        self.enrichment = enrichment or EnrichmentService()
        self.chunker = chunker or ChunkerService()
        self.embedder = embedder or EmbedderService()
        self.repository = repository or MemoryRepository()
        self.connections = connections or ConnectionService()

    async def capture_url(self, url: str, user: UserContext) -> AsyncGenerator[CaptureStreamEvent, None]:
        logger.info("capture accepted source_type=url user_id=%s url=%s", user.user_id, url)
        yield CaptureStreamEvent(type="progress", stage="accepted", message="URL capture accepted")
        try:
            logger.info("capture stage user_id=%s source_type=url stage=fetching", user.user_id)
            yield CaptureStreamEvent(type="progress", stage="fetching", message="Fetching and cleaning content")
            content = await self.fetcher.fetch_url(url)
            async for event in self._process_captured_content(content=content, user=user):
                yield event
        except Exception as exc:
            logger.error("capture failed source_type=url user_id=%s url=%s error=%s", user.user_id, url, exc)
            yield CaptureStreamEvent(type="error", stage="failed", message=str(exc))

    async def capture_text(self, text: str, title: str | None, user: UserContext) -> AsyncGenerator[CaptureStreamEvent, None]:
        logger.info("capture accepted source_type=text user_id=%s title=%s length=%s", user.user_id, title, len(text))
        yield CaptureStreamEvent(type="progress", stage="accepted", message="Text capture accepted")
        try:
            content = await self.fetcher.build_text_capture(text=text, title=title)
            async for event in self._process_captured_content(content=content, user=user):
                yield event
        except Exception as exc:
            logger.error("capture failed source_type=text user_id=%s title=%s error=%s", user.user_id, title, exc)
            yield CaptureStreamEvent(type="error", stage="failed", message=str(exc))

    async def capture_pdf(self, filename: str | None, pdf_bytes: bytes, user: UserContext) -> AsyncGenerator[CaptureStreamEvent, None]:
        logger.info("capture accepted source_type=pdf user_id=%s filename=%s bytes=%s", user.user_id, filename, len(pdf_bytes))
        yield CaptureStreamEvent(type="progress", stage="accepted", message="PDF capture accepted")
        try:
            logger.info("capture stage user_id=%s source_type=pdf stage=extracting", user.user_id)
            yield CaptureStreamEvent(type="progress", stage="extracting", message="Extracting text from PDF")
            content = await self.fetcher.build_pdf_capture(filename=filename, pdf_bytes=pdf_bytes)
            async for event in self._process_captured_content(content=content, user=user):
                yield event
        except Exception as exc:
            logger.error("capture failed source_type=pdf user_id=%s filename=%s error=%s", user.user_id, filename, exc)
            yield CaptureStreamEvent(type="error", stage="failed", message=str(exc))

    async def _process_captured_content(
        self,
        content: CapturedContent,
        user: UserContext,
    ) -> AsyncGenerator[CaptureStreamEvent, None]:
        if len(content.raw_content) < 80:
            logger.warning("capture rejected user_id=%s source_type=%s reason=content_too_short", user.user_id, content.source_type)
            raise ValueError("Captured content is too short to store as a memory")

        logger.info("capture stage user_id=%s source_type=%s stage=enriching", user.user_id, content.source_type)
        yield CaptureStreamEvent(type="progress", stage="enriching", message="Understanding key ideas and topics")
        enrichment_result = await self.enrichment.enrich(content.raw_content, title_hint=content.source_title)
        enrichment_payload = EnrichmentPayload(
            title=enrichment_result.title,
            summary=enrichment_result.summary,
            key_concepts=enrichment_result.key_concepts,
            topic_tags=enrichment_result.topic_tags,
            content_type=enrichment_result.content_type,
            importance_score=enrichment_result.importance_score,
            estimated_read_time=enrichment_result.estimated_read_time,
        )

        logger.info("capture stage user_id=%s source_type=%s stage=chunking", user.user_id, content.source_type)
        yield CaptureStreamEvent(type="progress", stage="chunking", message="Breaking content into retrieval chunks")
        chunks = await self.chunker.chunk(content.raw_content)
        if not chunks:
            logger.warning("capture rejected user_id=%s source_type=%s reason=no_chunks", user.user_id, content.source_type)
            raise ValueError("Unable to create chunks from the captured content")

        logger.info("capture stage user_id=%s source_type=%s stage=embedding chunks=%s", user.user_id, content.source_type, len(chunks))
        yield CaptureStreamEvent(type="progress", stage="embedding", message="Building memory embeddings")
        chunk_embeddings = await self.embedder.embed_texts(chunks)
        document_embedding = await self.embedder.embed_query(enrichment_payload.summary or content.raw_content[:4000])

        logger.info("capture stage user_id=%s source_type=%s stage=storing", user.user_id, content.source_type)
        yield CaptureStreamEvent(type="progress", stage="storing", message="Persisting memory and chunks")
        persisted = await self.repository.store_capture(
            user=user,
            payload=RepositoryCapturePayload(
                content=content,
                enrichment=enrichment_payload,
                chunks=chunks,
                chunk_embeddings=chunk_embeddings,
                document_embedding=document_embedding,
            ),
        )

        logger.info("capture stage user_id=%s source_type=%s stage=connecting memory_id=%s", user.user_id, content.source_type, persisted.memory_id)
        yield CaptureStreamEvent(type="progress", stage="connecting", message="Checking for related memories")
        connections = await self.connections.discover_for_memory(memory_id=persisted.memory_id, user_id=user.user_id)

        logger.info(
            "capture completed user_id=%s source_type=%s memory_id=%s xp=%s topics=%s connections=%s",
            user.user_id,
            content.source_type,
            persisted.memory_id,
            persisted.xp_awarded,
            len(persisted.topics_updated),
            len(connections),
        )
        yield CaptureStreamEvent(
            type="completed",
            stage="done",
            message="Capture complete",
            memory_id=persisted.memory_id,
            xp_awarded=persisted.xp_awarded,
            topics_updated=persisted.topics_updated,
            connections_found=len(connections),
        )
