import json
from sqlalchemy import create_engine, text
from .config import DB_PATH
from .models import Chunk, Document, Entity, Fact, Relationship
from .config import DATABASE_URL


SCHEMA = (
    "CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, filename TEXT NOT NULL, pages INTEGER NOT NULL, uploaded_at TEXT NOT NULL, status TEXT NOT NULL, dataset TEXT)",
    "CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, payload TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS entities (id TEXT PRIMARY KEY, payload TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS facts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS relationships (id TEXT PRIMARY KEY, payload TEXT NOT NULL)",
)


engine = create_engine(DATABASE_URL, future=True)


def connection():
    if DATABASE_URL.startswith("sqlite"):
        DB_PATH.parent.mkdir(exist_ok=True)
    db = engine.connect()
    for statement in SCHEMA:
        db.execute(text(statement))
    db.commit()
    return db


def save_document(document: Document) -> None:
    with connection() as db:
        db.execute(text("DELETE FROM documents WHERE id = :id"), {"id": document.id})
        db.execute(text("INSERT INTO documents VALUES (:id, :filename, :pages, :uploaded_at, :status, :dataset)"), {"id": document.id, "filename": document.filename, "pages": document.pages, "uploaded_at": document.uploaded_at.isoformat(), "status": document.status, "dataset": document.dataset})
        db.commit()


def save_facts(facts: list[Fact]) -> None:
    with connection() as db:
        for fact in facts:
            db.execute(text("DELETE FROM facts WHERE id = :id"), {"id": fact.id})
            db.execute(text("INSERT INTO facts VALUES (:id, :payload)"), {"id": fact.id, "payload": fact.model_dump_json()})
        db.commit()


def save_chunks(chunks: list[Chunk]) -> None:
    with connection() as db:
        for chunk in chunks:
            db.execute(text("DELETE FROM chunks WHERE id = :id"), {"id": chunk.id})
            db.execute(text("INSERT INTO chunks VALUES (:id, :payload)"), {"id": chunk.id, "payload": chunk.model_dump_json()})
        db.commit()


def save_entities(entities: list[Entity]) -> None:
    with connection() as db:
        for entity in entities:
            db.execute(text("DELETE FROM entities WHERE id = :id"), {"id": entity.id})
            db.execute(text("INSERT INTO entities VALUES (:id, :payload)"), {"id": entity.id, "payload": entity.model_dump_json()})
        db.commit()


def save_relationships(relationships: list[Relationship]) -> None:
    with connection() as db:
        db.execute(text("DELETE FROM relationships"))
        for item in relationships:
            db.execute(text("INSERT INTO relationships VALUES (:id, :payload)"), {"id": item.id, "payload": item.model_dump_json()})
        db.commit()


def load_layer() -> tuple[list[Document], list[Chunk], list[Entity], list[Fact], list[Relationship]]:
    with connection() as db:
        documents = [Document.model_validate(dict(row._mapping)) for row in db.execute(text("SELECT * FROM documents ORDER BY uploaded_at DESC"))]
        chunks = [Chunk.model_validate(json.loads(row._mapping["payload"])) for row in db.execute(text("SELECT payload FROM chunks"))]
        entities = [Entity.model_validate(json.loads(row._mapping["payload"])) for row in db.execute(text("SELECT payload FROM entities"))]
        facts = [Fact.model_validate(json.loads(row._mapping["payload"])) for row in db.execute(text("SELECT payload FROM facts"))]
        relationships = [Relationship.model_validate(json.loads(row._mapping["payload"])) for row in db.execute(text("SELECT payload FROM relationships"))]
    return documents, chunks, entities, facts, relationships


def clear_all() -> None:
    with connection() as db:
        db.execute(text("DELETE FROM documents"))
        db.execute(text("DELETE FROM chunks"))
        db.execute(text("DELETE FROM entities"))
        db.execute(text("DELETE FROM facts"))
        db.execute(text("DELETE FROM relationships"))
        db.commit()
