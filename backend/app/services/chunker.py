try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # pragma: no cover - optional at runtime
    RecursiveCharacterTextSplitter = None


class ChunkerService:
    def __init__(self, chunk_size: int = 1200, chunk_overlap: int = 200) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def chunk(self, content: str) -> list[str]:
        cleaned = content.strip()
        if not cleaned:
            return []

        if RecursiveCharacterTextSplitter is not None:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", ". ", " "],
            )
            chunks = [chunk.strip() for chunk in splitter.split_text(cleaned) if chunk.strip()]
            if chunks:
                return chunks

        paragraphs = [part.strip() for part in cleaned.split("\n\n") if part.strip()]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
            if len(candidate) <= self.chunk_size:
                current = candidate
                continue
            if current:
                chunks.append(current)
            current = paragraph
        if current:
            chunks.append(current)
        return chunks or [cleaned]
