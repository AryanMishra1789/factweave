import hashlib
import json
import re
from contextlib import contextmanager
from typing import Iterator

from .config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from .models import Chunk, Document, Entity, Fact, Relationship


def canonical(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", value.lower())).strip()


def build_entities(facts: list[Fact]) -> list[Entity]:
    entities: dict[str, Entity] = {}
    for fact in facts:
        name = fact.subject.strip()
        key = canonical(name)
        if not key:
            continue
        entity_id = hashlib.sha1(key.encode()).hexdigest()[:16]
        if entity_id not in entities:
            entities[entity_id] = Entity(id=entity_id, canonical_name=name, aliases=[])
        if name not in entities[entity_id].aliases and name != entities[entity_id].canonical_name:
            entities[entity_id].aliases.append(name)
    return list(entities.values())


class Neo4jGraph:
    """Neo4j persistence and traversal for the evidence-backed graph."""

    def __init__(self) -> None:
        self._driver = None
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        except Exception:
            self._driver = None

    @property
    def available(self) -> bool:
        if not self._driver:
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    @contextmanager
    def session(self) -> Iterator[object]:
        if not self._driver:
            raise RuntimeError("Neo4j driver is not installed")
        with self._driver.session(database=NEO4J_DATABASE) as session:
            yield session

    def sync(self, documents: list[Document], chunks: list[Chunk], entities: list[Entity], facts: list[Fact], relationships: list[Relationship]) -> None:
        if not self.available:
            raise RuntimeError("Neo4j is unavailable; start the graph database or configure NEO4J_URI")
        with self.session() as session:
            session.run("CREATE CONSTRAINT document_id IF NOT EXISTS FOR (n:Document) REQUIRE n.id IS UNIQUE")
            session.run("CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (n:Chunk) REQUIRE n.id IS UNIQUE")
            session.run("CREATE CONSTRAINT fact_id IF NOT EXISTS FOR (n:Fact) REQUIRE n.id IS UNIQUE")
            session.run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE")
            session.run("MATCH (n) DETACH DELETE n")
            for document in documents:
                session.run("MERGE (n:Document {id: $id}) SET n += $properties", id=document.id, properties=document.model_dump(mode="json"))
            for chunk in chunks:
                session.run("MERGE (n:Chunk {id: $id}) SET n += $properties WITH n MATCH (d:Document {id: $document_id}) MERGE (d)-[:CONTAINS]->(n)", id=chunk.id, document_id=chunk.document_id, properties=chunk.model_dump(mode="json"))
            for entity in entities:
                session.run("MERGE (n:Entity {id: $id}) SET n += $properties", id=entity.id, properties=entity.model_dump(mode="json"))
            for fact in facts:
                properties = fact.model_dump(mode="json")
                properties["evidence_json"] = json.dumps([item.model_dump(mode="json") for item in fact.evidence])
                session.run("MERGE (n:Fact {id: $id}) SET n += $properties", id=fact.id, properties=properties)
                entity_id = hashlib.sha1(canonical(fact.subject).encode()).hexdigest()[:16]
                session.run("MATCH (f:Fact {id: $fact_id}), (e:Entity {id: $entity_id}) MERGE (f)-[:ABOUT]->(e)", fact_id=fact.id, entity_id=entity_id)
                for evidence in fact.evidence:
                    evidence_id = hashlib.sha1(f"{fact.id}:{evidence.page_number}:{evidence.quote}".encode()).hexdigest()[:20]
                    session.run("MERGE (e:Evidence {id: $id}) SET e += $properties WITH e MATCH (f:Fact {id: $fact_id}) MERGE (f)-[:SUPPORTED_BY]->(e)", id=evidence_id, fact_id=fact.id, properties={**evidence.model_dump(mode="json"), "id": evidence_id})
            for relationship in relationships:
                session.run("MATCH (a:Fact {id: $source}), (b:Fact {id: $target}) MERGE (a)-[r:RELATES_TO {id: $id}]->(b) SET r.relation = $relation, r.confidence = $confidence, r.explanation = $explanation, r.shared_context = $context", source=relationship.source_fact_id, target=relationship.target_fact_id, id=relationship.id, relation=relationship.relation, confidence=relationship.confidence, explanation=relationship.explanation, context=relationship.shared_context)

    def snapshot(self) -> dict[str, list[dict]]:
        if not self.available:
            raise RuntimeError("Neo4j is unavailable")
        with self.session() as session:
            nodes = session.run("MATCH (n) RETURN labels(n) AS labels, properties(n) AS properties").data()
            edges = session.run("MATCH (a)-[r]->(b) RETURN a.id AS source, b.id AS target, type(r) AS type, properties(r) AS properties").data()
        return {"nodes": nodes, "edges": edges}


graph_store = Neo4jGraph()
