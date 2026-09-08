from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


FactType = Literal["numeric", "semantic", "entity", "event"]
RelationType = Literal["corroborates", "contradicts", "contextualizes", "unresolved"]


class Evidence(BaseModel):
    document_id: str
    document_name: str
    page_number: int
    quote: str
    char_start: int | None = None
    char_end: int | None = None
    locator: str = ""


class Chunk(BaseModel):
    id: str
    document_id: str
    document_name: str
    page_number: int
    text: str
    char_start: int
    char_end: int
    token_count: int


class Entity(BaseModel):
    id: str
    canonical_name: str
    entity_type: str = "unknown"
    aliases: list[str] = []


class VerificationResult(BaseModel):
    url: str
    status_code: int
    content_type: str | None = None
    excerpt: str
    retrieved_at: datetime
    trusted_domain: bool


class Fact(BaseModel):
    id: str
    subject: str
    predicate: str
    object: str
    fact_type: FactType
    normalized_value: float | str | None = None
    unit: str | None = None
    scope: str | None = None
    period: str | None = None
    confidence: float = Field(ge=0, le=1)
    evidence: list[Evidence]
    method: str = "rules"


class Relationship(BaseModel):
    id: str
    source_fact_id: str
    target_fact_id: str
    relation: RelationType
    confidence: float = Field(ge=0, le=1)
    explanation: str
    shared_context: list[str] = []


class Document(BaseModel):
    id: str
    filename: str
    pages: int
    uploaded_at: datetime
    status: str
    dataset: str | None = None


class KnowledgeLayer(BaseModel):
    documents: list[Document]
    chunks: list[Chunk] = []
    entities: list[Entity] = []
    facts: list[Fact]
    relationships: list[Relationship]
