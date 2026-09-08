from pathlib import Path
from .chunking import chunk_pages
from .extractor import read_pdf
from .graph import build_entities, graph_store
from .llm import extract_with_provider
from .models import Document
from .relations import compare_facts
from .store import save_chunks, save_document, save_entities, save_facts, save_relationships, load_layer


def process_pdf(document: Document, path: Path) -> tuple[int, int]:
    pages_count, pages = read_pdf(path)
    chunks = chunk_pages(document.id, document.filename, pages)
    facts = extract_with_provider(document.id, document.filename, chunks, pages)
    documents, existing_chunks, existing_entities, existing_facts, _ = load_layer()
    all_facts = existing_facts + facts
    relationships = compare_facts(all_facts)
    entities = build_entities(all_facts)
    document.pages = pages_count
    document.status = "processed"
    save_document(document)
    save_chunks(chunks)
    save_entities(entities)
    save_facts(facts)
    save_relationships(relationships)
    graph_store.sync(documents + [document], existing_chunks + chunks, entities, all_facts, relationships)
    return pages_count, len(facts)
