import hashlib
from .models import Chunk


def chunk_pages(document_id: str, filename: str, pages: list[tuple[int, str]], size: int = 900, overlap: int = 120) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page_number, text in pages:
        start = 0
        while start < len(text):
            end = min(len(text), start + size)
            content = text[start:end].strip()
            if content:
                chunk_id = hashlib.sha1(f"{document_id}:{page_number}:{start}:{content}".encode()).hexdigest()[:20]
                chunks.append(Chunk(id=chunk_id, document_id=document_id, document_name=filename, page_number=page_number, text=content, char_start=start, char_end=end, token_count=max(1, len(content.split()))))
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
    return chunks
