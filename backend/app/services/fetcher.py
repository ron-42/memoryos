import asyncio
import io
import logging
import re
from dataclasses import dataclass
from html import unescape
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from app.models.capture import CapturedContent

try:
    import fitz
except ImportError:  # pragma: no cover - optional at runtime
    fitz = None

SourceType = Literal["article", "pdf", "tweet", "reddit", "text"]
logger = logging.getLogger(__name__)
TRACKING_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "gclid",
    "fbclid",
    "si",
    "feature",
}
BLOCKED_CONTENT_PHRASES = (
    "warning: target url returned error 429",
    "too many requests",
    "our systems have detected unusual traffic from your computer network",
    "this page checks to see if it's really you sending the requests, and not a robot",
    "the block will expire shortly after those requests stop",
    "solve the above captcha",
)


def detect_source_type(value: str) -> SourceType:
    parsed = urlparse(value)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    if "twitter.com" in host or "x.com" in host:
        return "tweet"
    if "reddit.com" in host:
        return "reddit"
    if path.endswith(".pdf"):
        return "pdf"
    return "article"


def normalize_url(value: str) -> str:
    parsed = urlparse(value.strip())
    filtered_query = [(key, val) for key, val in parse_qsl(parsed.query, keep_blank_values=True) if key not in TRACKING_QUERY_PARAMS]
    normalized = parsed._replace(query=urlencode(filtered_query, doseq=True), fragment="")
    return urlunparse(normalized)


def normalize_text(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def build_reader_url(url: str) -> str:
    stripped = url.removeprefix("https://").removeprefix("http://")
    return f"https://r.jina.ai/http://{stripped}"


def is_youtube_url(value: str) -> bool:
    host = urlparse(value).netloc.lower()
    return "youtube.com" in host or "youtu.be" in host


def looks_like_blocked_content(value: str) -> bool:
    lowered = normalize_text(value).lower()
    if not lowered:
        return False
    if "warning: target url returned error 429" in lowered:
        return True
    hits = sum(1 for phrase in BLOCKED_CONTENT_PHRASES if phrase in lowered)
    return hits >= 2


def build_blocked_content_message(source_type: SourceType) -> str:
    return "This source blocked automated access, so MemoryOS could not capture usable content."


def extract_pdf_text(pdf_bytes: bytes) -> str:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed")

    with fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf") as document:
        pages = [page.get_text("text") for page in document]
    return normalize_text("\n\n".join(pages))


def _strip_html(html: str) -> str:
    cleaned = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    cleaned = re.sub(r"(?is)<style.*?>.*?</style>", " ", cleaned)
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</p>", "\n\n", cleaned)
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    return normalize_text(unescape(cleaned))


def _extract_title(html: str) -> str | None:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    if not match:
        return None
    return normalize_text(unescape(match.group(1)))[:200] or None


@dataclass(slots=True)
class FetcherService:
    timeout_seconds: float = 25.0

    async def fetch_url(self, url: str) -> CapturedContent:
        normalized_url = normalize_url(url)
        if is_youtube_url(normalized_url):
            raise ValueError("YouTube URLs are not supported in v1. Use article URLs, PDF uploads, or pasted text.")
        source_type = detect_source_type(normalized_url)

        if source_type == "pdf":
            return await self._fetch_pdf_url(normalized_url)
        return await self._fetch_reader_content(normalized_url, source_type)

    async def build_text_capture(self, text: str, title: str | None = None) -> CapturedContent:
        content = normalize_text(text)
        return CapturedContent(source_type="text", source_title=title, raw_content=content)

    async def build_pdf_capture(self, filename: str | None, pdf_bytes: bytes) -> CapturedContent:
        content = await asyncio.to_thread(extract_pdf_text, pdf_bytes)
        if not content:
            raise ValueError("The PDF did not contain extractable text")
        return CapturedContent(source_type="pdf", source_title=filename, raw_content=content)

    async def _fetch_pdf_url(self, url: str) -> CapturedContent:
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
        content = await asyncio.to_thread(extract_pdf_text, response.content)
        if not content:
            raise ValueError("The PDF did not contain extractable text")
        return CapturedContent(source_type="pdf", source_url=url, raw_content=content)

    async def _fetch_reader_content(self, url: str, source_type: SourceType) -> CapturedContent:
        reader_error: Exception | None = None
        blocked_message = build_blocked_content_message(source_type)
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            try:
                reader_response = await client.get(build_reader_url(url))
                reader_response.raise_for_status()
                reader_text = normalize_text(reader_response.text)
                if looks_like_blocked_content(reader_text):
                    logger.warning("reader fallback blocked source_type=%s url=%s", source_type, url)
                    reader_error = RuntimeError(blocked_message)
                elif len(reader_text) >= 80:
                    return CapturedContent(source_type=source_type, source_url=url, raw_content=reader_text)
            except Exception as exc:  # pragma: no cover - network-dependent
                reader_error = exc

            fallback_response = await client.get(url)
            fallback_response.raise_for_status()
            content_type = fallback_response.headers.get("content-type", "").lower()
            if "application/pdf" in content_type:
                content = await asyncio.to_thread(extract_pdf_text, fallback_response.content)
                return CapturedContent(source_type="pdf", source_url=url, raw_content=content)

            html = fallback_response.text
            text = _strip_html(html)
            if looks_like_blocked_content(html) or looks_like_blocked_content(text):
                logger.warning("html fallback blocked source_type=%s url=%s", source_type, url)
                raise RuntimeError(blocked_message)
            if not text:
                if reader_error:
                    raise RuntimeError("Unable to extract usable content from the URL") from reader_error
                raise RuntimeError("Unable to extract usable content from the URL")

            return CapturedContent(
                source_type=source_type,
                source_url=url,
                source_title=_extract_title(html),
                raw_content=text,
            )
