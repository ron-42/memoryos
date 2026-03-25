import asyncio
import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass

from app.core.config import get_settings

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - optional at runtime
    genai = None

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EnrichmentResult:
    title: str | None
    summary: str
    key_concepts: list[str]
    topic_tags: list[str]
    content_type: str | None
    importance_score: float | None
    estimated_read_time: int | None


class EnrichmentService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def enrich(self, content: str, title_hint: str | None = None) -> EnrichmentResult:
        if self.settings.gemini_api_key and genai is not None:
            try:
                return await self._enrich_with_gemini(content=content, title_hint=title_hint)
            except Exception:
                logger.exception("gemini enrichment failed")
        return self._fallback_enrichment(content=content, title_hint=title_hint)

    async def _enrich_with_gemini(self, content: str, title_hint: str | None = None) -> EnrichmentResult:
        prompt = f"""
Analyze the following captured content and return strict JSON only with keys:
title, summary, key_concepts, topic_tags, content_type, importance_score, estimated_read_time.

Rules:
- summary must be 2-3 sentences
- key_concepts max 8
- topic_tags max 3 and broad
- content_type must be one of technical, opinion, research, news, tutorial
- importance_score must be a float from 0 to 10
- estimated_read_time is minutes
- use the provided title hint when useful: {title_hint or "none"}

Content:
{content[:12000]}
""".strip()

        def _run() -> EnrichmentResult:
            genai.configure(api_key=self.settings.gemini_api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            payload = json.loads(response.text)
            return EnrichmentResult(
                title=payload.get("title") or title_hint,
                summary=(payload.get("summary") or "").strip(),
                key_concepts=list(payload.get("key_concepts") or [])[:8],
                topic_tags=list(payload.get("topic_tags") or [])[:3],
                content_type=payload.get("content_type"),
                importance_score=float(payload["importance_score"]) if payload.get("importance_score") is not None else None,
                estimated_read_time=int(payload["estimated_read_time"]) if payload.get("estimated_read_time") is not None else None,
            )

        return await asyncio.to_thread(_run)

    def _fallback_enrichment(self, content: str, title_hint: str | None = None) -> EnrichmentResult:
        clean = content.strip()
        title = title_hint or self._infer_title(clean)
        summary = self._summarize(clean)
        key_concepts = self._extract_concepts(clean)
        topic_tags = self._infer_topics(clean)
        estimated_read_time = max(1, math.ceil(len(clean.split()) / 220))
        importance_score = min(10.0, round(4.5 + min(len(clean.split()) / 400, 5.0), 1))
        content_type = self._infer_content_type(clean)
        return EnrichmentResult(
            title=title,
            summary=summary,
            key_concepts=key_concepts,
            topic_tags=topic_tags,
            content_type=content_type,
            importance_score=importance_score,
            estimated_read_time=estimated_read_time,
        )

    def _infer_title(self, content: str) -> str | None:
        first_line = content.splitlines()[0].strip() if content.splitlines() else ""
        if 4 <= len(first_line) <= 120:
            return first_line
        return "Untitled capture"

    def _summarize(self, content: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", content)
        summary_sentences = [sentence.strip() for sentence in sentences if sentence.strip()][:3]
        if not summary_sentences:
            summary_sentences = [content[:240].strip()]
        return " ".join(summary_sentences)[:600]

    def _extract_concepts(self, content: str) -> list[str]:
        words = re.findall(r"[A-Za-z][A-Za-z0-9/+.-]{2,}", content.lower())
        stop_words = {
            "this", "that", "with", "from", "have", "about", "their", "there", "which", "into",
            "would", "could", "should", "your", "what", "when", "where", "while", "using",
            "after", "before", "because", "through", "being", "article", "video",
        }
        counts = Counter(word for word in words if word not in stop_words)
        return [word for word, _ in counts.most_common(8)]

    def _infer_topics(self, content: str) -> list[str]:
        lowered = content.lower()
        topic_rules = [
            ("AI/ML", {"llm", "model", "embedding", "rag", "agent", "neural", "inference"}),
            ("Engineering", {"api", "backend", "frontend", "database", "python", "typescript", "system"}),
            ("Startups", {"startup", "founder", "market", "growth", "pricing", "company"}),
            ("Psychology", {"habit", "behavior", "mindset", "attention", "memory", "learning"}),
            ("Research", {"paper", "study", "experiment", "dataset", "method", "analysis"}),
        ]
        tags = [name for name, keywords in topic_rules if any(keyword in lowered for keyword in keywords)]
        return tags[:3] or ["General"]

    def _infer_content_type(self, content: str) -> str:
        lowered = content.lower()
        if any(term in lowered for term in {"paper", "study", "methodology", "experiment"}):
            return "research"
        if any(term in lowered for term in {"how to", "step-by-step", "tutorial", "guide"}):
            return "tutorial"
        if any(term in lowered for term in {"opinion", "i think", "in my view"}):
            return "opinion"
        if any(term in lowered for term in {"breaking", "announced", "today", "reported"}):
            return "news"
        return "technical"
