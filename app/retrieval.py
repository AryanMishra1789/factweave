import math
import re
from collections import Counter
from .models import Chunk


STOPWORDS = {"the", "and", "for", "with", "that", "from", "this", "were", "was", "are", "has", "have", "into", "its"}


def terms(text: str) -> list[str]:
    return [term for term in re.findall(r"[a-z0-9]{2,}", text.lower()) if term not in STOPWORDS]


def retrieve(chunks: list[Chunk], query: str, limit: int = 8) -> list[tuple[Chunk, float]]:
    query_terms = Counter(terms(query))
    if not query_terms:
        return []
    document_frequency = Counter()
    chunk_terms: dict[str, Counter[str]] = {}
    for chunk in chunks:
        counts = Counter(terms(chunk.text))
        chunk_terms[chunk.id] = counts
        document_frequency.update(counts.keys())
    total = max(len(chunks), 1)
    scored: list[tuple[Chunk, float]] = []
    for chunk in chunks:
        counts = chunk_terms[chunk.id]
        score = 0.0
        for term, query_count in query_terms.items():
            if term in counts:
                idf = math.log((total + 1) / (document_frequency[term] + 1)) + 1
                score += (1 + math.log(counts[term])) * idf * query_count
        if score:
            scored.append((chunk, round(score, 4)))
    return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]