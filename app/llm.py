import json
from .config import FACTWEAVE_EXTRACTION_MODE, FACTWEAVE_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL
from .models import Chunk, Fact
from .extractor import extract_facts


SYSTEM_PROMPT = """Extract only claims explicitly supported by the supplied passage. Return JSON with a facts array. Each fact must have subject, predicate, object, fact_type, normalized_value, unit, scope, period, confidence. Never infer a value that is not in the passage."""


def extract_with_provider(document_id: str, filename: str, chunks: list[Chunk], fallback_pages: list[tuple[int, str]]) -> list[Fact]:
    if FACTWEAVE_EXTRACTION_MODE != "llm" or not OPENAI_API_KEY:
        return extract_facts(document_id, filename, fallback_pages)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)
        facts: list[Fact] = []
        for chunk in chunks:
            response = client.chat.completions.create(model=FACTWEAVE_MODEL, temperature=0, response_format={"type": "json_object"}, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": chunk.text}])
            payload = json.loads(response.choices[0].message.content or "{}")
            for index, item in enumerate(payload.get("facts", [])):
                facts.append(Fact(id=f"{chunk.id}-{index}", subject=str(item.get("subject", "")).strip(), predicate=str(item.get("predicate", "")).strip(), object=str(item.get("object", "")).strip(), fact_type=item.get("fact_type", "semantic"), normalized_value=item.get("normalized_value"), unit=item.get("unit"), scope=item.get("scope"), period=item.get("period"), confidence=min(float(item.get("confidence", 0.5)), 0.95), method="llm", evidence=[{"document_id": document_id, "document_name": filename, "page_number": chunk.page_number, "quote": chunk.text, "char_start": chunk.char_start, "char_end": chunk.char_end, "locator": f"Page {chunk.page_number}"}]))
        return facts or extract_facts(document_id, filename, fallback_pages)
    except Exception:
        # Provider failure must not make the evidence layer unavailable.
        return extract_facts(document_id, filename, fallback_pages)
