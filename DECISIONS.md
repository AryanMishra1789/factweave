# Architecture Decisions

This document explains why Factweave uses each major part of the design.

## Start with facts, not chat

The assignment is about discovering claims, grounding them in documents, and comparing them. A chatbot can hide all three steps behind generated text.

Factweave therefore stores structured facts first:

```text
subject + predicate + object + value + unit + period + evidence
```

The UI and APIs expose the evidence and relationship explanation directly.

## Why RAG

Large PDFs need a way to find relevant passages without sending the whole document to an extractor or model. RAG provides that retrieval layer.

In Factweave, retrieval is deliberately separate from judgment:

```text
query -> ranked source chunks -> fact extraction or review
```

Retrieval does not decide that two facts contradict each other. That decision belongs to the resolution engine, where values, units, periods, and scope can be compared explicitly.

The current retriever is BM25-style lexical search. It is free, deterministic, and easy to inspect. An embedding index can be added later without changing the fact or evidence contracts.

## Why a knowledge graph

A fact is more useful when it can be traversed:

```text
document -> evidence -> fact -> entity
                         |
                         -> related fact -> relationship
```

The graph supports questions such as:

- Which documents mention this entity?
- Which facts support or contradict this fact?
- What evidence is behind this relationship?

The graph is part of the reasoning model, not a visual extra. The difficult part remains extraction and evidence grounding; the graph makes the resulting facts and relationships traversable and reusable by the UI, API, and agents.

Neo4j is the graph system of record. PostgreSQL remains the structured evidence store. The ingestion pipeline writes both stores: PostgreSQL keeps document and fact payloads, while Neo4j owns graph traversal across evidence, entities, facts, and relationships.

## Why LLM-assisted extraction

LLMs are useful for varied language, semantic claims, and normalization across inconsistent report wording. They can also invent facts or lose provenance, so they are constrained by chunk-level evidence and structured output.

The structured LLM adapter is the semantic extraction path. The deterministic extractor handles clear numeric report patterns and acts as a controlled fallback when a provider is unavailable or a claim is better handled by a rule. This is an implementation fallback, not the product definition: the architecture is LLM-assisted fact extraction with evidence constraints.

The LLM is an extractor and ambiguity helper, not the source of truth. A claim without evidence is not accepted as a useful result. This gives the evaluator a clear distinction between language understanding and fact resolution.

## Why a fact resolution engine

Retrieval can find two passages, but it cannot reliably classify their relationship. The resolution engine compares normalized facts.

It uses deterministic checks first:

- same meaningful subject;
- compatible predicate;
- numeric value difference;
- unit comparison;
- period comparison;
- scope context where available.

The output is one of:

- `corroborates`;
- `contradicts`;
- `contextualizes`.

An explanation and confidence accompany the classification. When the system cannot establish equivalence safely, it should remain uncertain rather than force a conclusion.

## Why MCP

MCP is useful at the tool boundary, not in the PDF ingestion core.

The same knowledge layer can be used by:

- the browser UI;
- REST clients;
- an AI agent using MCP.

The optional MCP adapter exposes operations such as searching facts and finding contradictions. Keeping it outside ingestion means the system still works when no agent is connected, and agents do not need a second copy of the business logic.

## Why the generic API caller

Uploaded documents may not contain enough evidence to verify a claim. An external source can sometimes provide enrichment or confirmation.

The API caller is optional and is not part of the core fact pipeline. It is restricted by design:

- HTTPS only;
- explicit domain allowlist;
- request timeout;
- response size limit;
- no credentials forwarded from the application.

This prevents an unrestricted URL fetcher from becoming a server-side request forgery risk. It also keeps the assignment demo functional when no external service is available.

## Why Flask

Flask is small and explicit. The project has a modest number of routes, and the framework makes the boundary easy to understand for a reviewer.

The application separates HTTP concerns from extraction, retrieval, storage, and reasoning services. Moving to another web framework later would not require rewriting the domain logic.

## Why PostgreSQL and SQLite

PostgreSQL is the durable deployment choice because it supports concurrent access, transactions, JSON data, indexes, and a future vector extension such as pgvector.

SQLite is the local fallback because a reviewer can run the project without installing a database server. Both modes use the same SQLAlchemy repository boundary.

## Why SQLAlchemy

SQLAlchemy keeps database-specific details out of the pipeline. It supports SQLite for local setup and PostgreSQL for deployment without duplicating persistence code.

The current repository is intentionally small. A production version would add migrations, typed database tables, indexes, and background job state.

## Why PyMuPDF

PyMuPDF is fast, easy to install, and preserves page boundaries and text offsets. Those properties matter more here than treating a PDF as one large text blob.

OCR and layout-aware table extraction can be added behind the same ingestion boundary later.

## Why Pydantic models

Pydantic models define the contracts shared by extraction, storage, REST responses, and MCP tools. They validate confidence ranges and keep fact payloads consistent across optional extraction providers.

## Why not microservices

The assignment rewards a clear working system. Separate services for ingestion, retrieval, extraction, graph storage, and reasoning would add deployment and debugging overhead without improving the core demonstration.

The code keeps boundaries between those responsibilities inside one application. They can be split later if workload or team ownership requires it.

## Why synchronous processing for now

Synchronous processing makes the upload flow easy to follow and suitable for the supplied excerpts. A large production workload should move PDF processing and LLM calls to a durable queue with retries and progress updates.

That is an execution concern, not a reason to hide the core pipeline behind unnecessary infrastructure in the assignment prototype.

## Decision summary

| Area | Decision | Reason |
|---|---|---|
| Web | Flask | Small, explicit HTTP boundary |
| Storage | PostgreSQL with SQLite fallback | Durable deployment and zero-setup local mode |
| PDF parsing | PyMuPDF | Page and offset provenance |
| Retrieval | BM25-style lexical search | Free, deterministic, inspectable |
| Extraction | Conservative rules plus optional LLM | Reproducibility with higher-recall extension |
| Relationships | Deterministic resolution first | Explainable comparisons |
| Graph | Neo4j graph database | Direct traversal and relationship modeling; requires a second persistence service |
| Agent access | Optional MCP adapter | Reuse the same knowledge services |
| External evidence | Allowlisted HTTPS caller | Optional enrichment with security boundaries |
| Deployment shape | One application | Understandable prototype with clear internal boundaries |