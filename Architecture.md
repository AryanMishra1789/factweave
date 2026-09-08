# Factweave Architecture

## 1. Purpose

Factweave is an evidence-first fact knowledge layer for PDF documents.

Its job is to:

1. ingest one or more PDFs;
2. preserve document and page provenance;
3. discover numerical and semantic candidates;
4. normalize facts so they can be compared;
5. identify corroboration, contradiction, and contextual difference;
6. expose the results through a web UI, REST API, and optional MCP tools.

It is deliberately not a conventional PDF chatbot. Retrieval provides source context, but the system stores structured facts and evaluates relationships between facts.

## 2. System overview

```text
                         PDF upload
                              |
                              v
                   +------------------------+
                   | Flask upload endpoint   |
                   | type and size checks    |
                   +-----------+------------+
                               |
                               v
                   +------------------------+
                   | Document ingestion     |
                   | PyMuPDF page reading   |
                   +-----------+------------+
                               |
                               v
                   +------------------------+
                   | Chunking and metadata  |
                   | page, offsets, tokens  |
                   +-----------+------------+
                               |
                 +-------------+-------------+
                 |                           |
                 v                           v
       +-------------------+       +----------------------+
       | Evidence retrieval|       | Fact extraction      |
       | BM25-style search |       | local rules or LLM   |
       +---------+---------+       +----------+-----------+
                 |                            |
                 |                            v
                 |                 +----------------------+
                 |                 | Normalized facts    |
                 |                 | units, periods,     |
                 |                 | scope, confidence  |
                 |                 +----------+-----------+
                 |                            |
                 +----------------------------+
                                              v
                                  +----------------------+
                                  | Evidence and graph  |
                                  | entities, facts,     |
                                  | relationships        |
                                  +----------+-----------+
                                             |
                                             v
                                  +----------------------+
                                  | Resolution engine    |
                                  | corroborates,        |
                                  | contradicts,         |
                                  | contextualizes       |
                                  +----------+-----------+
                                             |
                    +------------------------+------------------------+
                    |                        |                         |
                    v                        v                         v
              Web UI                  REST API                  MCP adapter
                                                                     |
                                                                     v
                                                              AI agents/tools
```

## 3. Repository layout

```text
app/
  main.py          Flask routes and HTTP boundary
  config.py        Environment-based configuration
  models.py        Pydantic domain contracts
  extractor.py     PDF text extraction and local fact extraction
  chunking.py      Page-aware overlapping chunks
  retrieval.py     BM25-style local retrieval
  llm.py           Optional OpenAI-compatible structured extraction
  graph.py         Canonical entity construction
  relations.py     Cross-document relationship reasoning
  pipeline.py      Ingestion orchestration
  store.py         SQLAlchemy persistence repository
  verifier.py      Controlled external verification
  mcp_server.py    Optional stdio MCP adapter
  static/          Browser UI

scripts/
  seed_starter_data.py  Process the supplied PDFs
  evaluate.py           Run the behavioral evaluation cases

tests/
  test_core.py          Unit tests for extraction and reasoning

starter-datasets/
  Supplied Delhivery and India macroeconomy PDFs
```

## 4. Ingestion flow

### 4.1 Upload boundary

`POST /api/documents` accepts one PDF through a multipart form field named `file`.

The boundary performs:

- extension validation;
- filename sanitization with `Path(filename).name`;
- a 50 MB Flask request limit;
- storage under an internal generated document id rather than the user filename.

The original filename is retained as metadata for evidence display.

### 4.2 PDF parsing

`app/extractor.py` uses PyMuPDF to read each page and returns:

```text
(page_number, normalized_page_text)
```

Page numbers are retained because page-level provenance is more useful to a reviewer than a document-level citation. Character offsets are also retained when a candidate is extracted from a page.

The current parser handles text-based PDFs. Scanned pages and complex tables are not fully supported yet; the system should abstain rather than invent facts in those cases.

### 4.3 Chunking

`app/chunking.py` splits each page into overlapping chunks. Each chunk stores:

- chunk id;
- document id and filename;
- page number;
- text;
- character start and end offsets;
- approximate token count.

Chunks do not cross page boundaries. This makes evidence easier to inspect and prevents a quote from combining unrelated pages.

Overlap reduces the chance that a fact split at a chunk boundary loses context. The current chunk size is intentionally simple and can be tuned without changing the domain model.

## 5. Retrieval layer

`app/retrieval.py` implements a small BM25-style lexical retriever.

It uses:

- tokenization;
- stopword removal;
- term frequency;
- inverse document frequency;
- a ranked result list.

The endpoint is:

```text
GET /api/search?q=inflation&limit=8
```

The response contains both ranked chunks and directly matching structured facts.

### Why lexical retrieval instead of embeddings?

The starter project is intended to run without credentials or paid services. A lexical retriever has several advantages for this prototype:

- deterministic behavior;
- no model download or API dependency;
- easy debugging when a result is wrong;
- low operational cost;
- useful performance for a small document collection.

The trade-off is weaker semantic matching. A production version could add embeddings and pgvector as a second retriever, but lexical retrieval should remain available as a transparent fallback.

Most importantly, retrieval does not decide whether two facts contradict each other. It only supplies relevant evidence.

## 6. Fact extraction and normalization

### 6.1 Local extraction

The default extractor uses conservative patterns for common report language such as:

```text
Revenue was 120 crore.
The company reported revenue of INR 120 crore.
Revenue stood at 4.2 percent.
```

Each extracted fact contains:

- `subject`;
- `predicate`;
- `object`;
- `fact_type`;
- `normalized_value`;
- `unit`;
- `scope`;
- `period`;
- `confidence`;
- extraction method;
- one or more evidence records.

The local extractor intentionally rejects generic sentence fragments and broad semantic patterns when they are likely to produce unsupported claims.

### 6.2 Optional LLM extraction

`app/llm.py` provides an optional OpenAI-compatible structured-output adapter.

It is enabled only when:

```text
FACTWEAVE_EXTRACTION_MODE=llm
OPENAI_API_KEY is configured
```

The LLM receives a chunk and is instructed to return structured facts supported by that chunk. The resulting fact still stores the complete chunk as evidence with page and offset metadata.

If the provider fails, the adapter falls back to the local extractor. This keeps ingestion available and prevents a provider outage from destroying the evidence workflow.

### Why the LLM is optional

The assignment permits any technology but does not require a paid model. Keeping the core pipeline provider-independent makes the project:

- free to run;
- reproducible by a reviewer;
- easier to debug;
- less exposed to model availability and rate limits.

The trade-off is lower semantic recall in local mode. The correct production direction is to use the LLM for ambiguous or low-confidence candidates, not to let it replace evidence and deterministic validation.

## 7. Evidence and provenance

Evidence is part of the fact contract, not an optional UI decoration.

Each evidence record contains:

```text
document_id
document_name
page_number
quote
char_start
char_end
locator
```

A relationship is only useful if a reviewer can inspect both source passages. Relationship responses therefore include the relationship explanation and the two related fact records, including their evidence.

Available evidence routes include:

```text
GET /api/facts/<fact_id>
GET /api/facts/<fact_id>/evidence
```

This design supports auditability: a user can move from a classification to the exact passage that caused it.

## 8. Knowledge graph model

The logical graph contains four kinds of nodes:

```text
Document -> Chunk -> Evidence -> Fact -> Entity
                                      |
                                      v
                                Relationship
```

### Entities

`app/graph.py` creates canonical entities from fact subjects. Canonicalization lowercases text, removes punctuation, and collapses whitespace. The entity id is a stable hash of the canonical name.

This is deliberately modest. It is enough to expose structured traversal and avoid hard-coding the starter documents, but it is not a full entity-resolution system.

### Facts

Facts remain first-class records rather than being reduced to graph edges. This matters because a fact carries values, context, confidence, method, and evidence.

### Relationships

Relationships connect two facts and contain:

- source fact id;
- target fact id;
- relation type;
- confidence;
- explanation;
- shared context.

The graph endpoint is:

```text
GET /api/graph
```

### Why PostgreSQL instead of Neo4j?

The project does not need a graph database to satisfy the assignment. Facts and evidence are naturally document-shaped, and the current graph is a projection used for traversal and comparison.

PostgreSQL with SQLAlchemy was chosen because it:

- keeps deployment simple;
- supports durable relational data;
- avoids adding a second database for a small prototype;
- can later use JSONB, indexes, and pgvector;
- is familiar to most teams.

Neo4j would make graph traversal more natural, but it would add operational complexity without solving the central extraction and evidence problem. A graph database becomes more attractive if relationship traversal becomes the primary workload.

## 9. Fact resolution

`app/relations.py` compares facts from different documents.

### Candidate blocking

The engine first groups facts by normalized subject and predicate. This avoids comparing every fact with every other fact and reduces unrelated comparisons as the knowledge layer grows.

### Subject and predicate matching

The current matcher requires meaningful subject-token overlap and compatible predicates. Generic words are ignored. Broad sentence fragments are rejected before they reach this stage.

This is intentionally conservative. A false contradiction is more damaging than an unresolved relationship in a financial document workflow.

### Relation rules

#### Corroborates

Two facts corroborate when their values are close enough or their normalized objects match, with no conflicting period or unit context.

#### Contradicts

Two facts contradict when:

- they refer to the same apparent subject and predicate;
- they come from different documents;
- their values differ materially;
- no period or unit context explains the difference.

#### Contextualizes

Two facts contextualize one another when values differ but the evidence contains a different period or unit. This avoids collapsing time-varying or differently measured facts into a false contradiction.

### Uncertainty

Every relationship has a confidence score and an explanation. The engine does not claim that a relationship is a universal truth; it records why the current comparison was made.

For difficult semantic cases, the intended extension is an LLM judge constrained by the two evidence passages and the normalized metadata. Deterministic checks should remain the first pass.

## 10. Persistence

`app/store.py` uses SQLAlchemy with a small repository boundary.

The current tables are:

```text
documents
chunks
entities
facts
relationships
```

Payloads are stored as JSON strings inside the repository. This keeps the prototype schema flexible while the Pydantic models define the application contract.

### SQLite mode

SQLite is the default local mode because it has zero setup and is sufficient for a reviewer running the project on a laptop.

### PostgreSQL mode

Set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL or run `docker compose up --build`.

PostgreSQL is the intended durable deployment database. A production version should replace the lightweight startup schema creation with Alembic migrations and add indexes for document ids, relation types, periods, and normalized entities.

## 11. API and UI

Flask is the HTTP boundary. The browser UI uses the same API as external clients.

The UI supports:

- PDF upload and drag-and-drop;
- document, fact, and evidence counts;
- relationship filters;
- relationship explanations;
- source quotes from both sides of a finding;
- grounded evidence search;
- fact provenance display.

The UI does not present a chat answer that hides the reasoning chain. It presents findings that can be opened and inspected.

## 12. MCP tool layer

`app/mcp_server.py` is an optional stdio adapter using the MCP SDK.

It exposes tools over the same repository services:

- `search_facts`;
- `find_contradictions`.

The Flask API also exposes MCP-shaped HTTP routes for simple demonstrations.

MCP is kept outside the ingestion core. This is intentional: document processing should work even when no AI agent is connected, while agents can consume the knowledge layer when useful.

## 13. External verification

`app/verifier.py` provides optional external source verification.

The verifier enforces:

- HTTPS only;
- explicit domain allowlisting;
- request timeout;
- response size limit;
- a small response excerpt;
- no secrets passed to the target URL.

External verification is never required for the core result. Uploaded documents remain the primary evidence source.

This prevents a generic API caller from becoming an unrestricted server-side request forgery surface.

## 14. Incremental processing

Each PDF is assigned a new document id and processed independently.

The pipeline:

1. reads the new PDF;
2. writes its chunks;
3. extracts its facts;
4. rebuilds canonical entities;
5. compares the expanded fact set;
6. replaces the derived relationship set.

No source PDF needs to be re-parsed when a new document is uploaded. The current relationship recomputation is acceptable for the prototype, but a larger system should persist candidate blocks and update only affected relationship groups.

## 15. Testing and evaluation

The project includes two types of checks.

### Unit tests

`tests/test_core.py` covers:

- page evidence preservation;
- contradiction classification;
- retrieval ranking;
- entity canonicalization;
- verifier URL rejection.

### Behavioral evaluation

`scripts/evaluate.py` checks four required behaviors:

- corroboration;
- contradiction;
- contextual difference;
- extraction abstention.

The evaluation uses small explicit fixtures so a change to the reasoning rules has a visible effect. A stronger future evaluation would add a labeled set of facts from the starter PDFs and measure extraction precision, evidence accuracy, and relationship precision separately.

## 16. Security and reliability decisions

- Credentials are read from environment variables and are not committed.
- PDF filenames do not control storage paths.
- Uploads are limited to PDFs and capped at 50 MB.
- External verification requires HTTPS and an allowlist.
- Provider errors fall back to local extraction.
- Unsupported content is allowed to produce no fact.
- Evidence is stored with every fact.
- Relationship explanations are returned with relationship results.

## 17. Main trade-offs

| Decision | Chosen approach | Trade-off |
|---|---|---|
| Web framework | Flask | Small and explicit; fewer built-in API conventions than FastAPI |
| Local database | SQLite | Easy setup; not suitable for concurrent production writes |
| Deployment database | PostgreSQL | Durable and extensible; requires a database service |
| Retrieval | Lexical BM25-style ranking | Transparent and free; weaker semantic recall than embeddings |
| Fact extraction | Conservative rules with optional LLM | Reproducible fallback; lower local semantic coverage |
| Graph storage | Relational graph projection | Simple operations; less natural than a graph database for deep traversal |
| Processing | Synchronous upload pipeline | Easy to understand; large PDFs should move to background jobs |
| Evidence | Page and quote references | Auditable; table and OCR evidence need richer layout metadata |
| Verification | Allowlisted HTTPS fetch | Safer than arbitrary requests; cannot verify unknown domains |
| MCP | Optional adapter outside core | Keeps the core independent; requires separate MCP installation |

