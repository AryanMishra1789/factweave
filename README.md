# Factweave

**An evidence-first fact knowledge layer for PDFs.** Factweave turns report prose into structured claims, preserves the exact page evidence behind each claim, and compares claims across documents without pretending every difference is a contradiction.

## Why this approach

The assignment is about grounded reasoning, not a PDF chatbot. Factweave uses explicit retrieval, knowledge, reasoning, and tool layers:

1. **Retrieval layer**: page text is split into overlapping chunks and ranked with a lightweight BM25-style lexical retriever. Retrieval supplies evidence candidates; it does not decide truth.
2. **Knowledge layer**: documents, chunks, entities, facts, evidence spans, and relationships are persisted in PostgreSQL through SQLAlchemy.
3. **Reasoning layer**: facts are normalized into subject/predicate/object plus value, unit, period, scope, and confidence. Deterministic checks classify pairs as `corroborates`, `contradicts`, or `contextualizes`.
4. **Tool layer**: Flask exposes REST endpoints and an optional stdio MCP server over the same services.

The default extractor is deterministic and credential-free. For higher recall, set `FACTWEAVE_EXTRACTION_MODE=llm` and `OPENAI_API_KEY` to use the optional OpenAI-compatible structured-output adapter. Provider failures fall back to the local extractor, and every LLM-produced claim still requires a chunk-level evidence passage.

## Run locally

Requires Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:DATABASE_URL = "sqlite:///$(Resolve-Path .factweave/factweave.db)"
flask --app app.main run --debug
```

Open http://127.0.0.1:5000. Upload any PDF, or seed the supplied datasets:

```powershell
python scripts/seed_starter_data.py
python scripts/evaluate.py
```

For the production-shaped PostgreSQL path:

```powershell
docker compose up --build
```

Then open http://127.0.0.1:8000. The database is configured by `DATABASE_URL`; credentials are not committed.

## API surface

- `GET /health` - liveness check.
- `POST /api/documents` - multipart upload with field name `file`.
- `GET /api/layer` - documents, facts, evidence, and relationships.
- `GET /api/search?q=inflation` - ranked evidence chunks and matching facts.
- `GET /api/graph` - entities, facts, and relationships for structured traversal.
- `POST /api/verify` - guarded external verification; HTTPS and an allowlist are required.
- `GET /api/mcp/tools` - discover agent-facing tools.
- `GET /api/mcp/find-contradictions` - return contradiction relationships with both facts and evidence.

Run the stdio MCP adapter with `pip install -e ".[agent]"` followed by `python -m app.mcp_server`. It exposes `search_facts` and `find_contradictions` without duplicating business logic.

## The four required cases

The starter datasets are deliberately useful for showing all four cases. After running the seed script, use the relationship filters in the UI and open the evidence cards.

### 1. Corroboration

Two independent reports may state the same metric with different wording, such as a revenue or macroeconomic growth claim. The extractor normalizes the subject, predicate, numeric value, and unit; the comparator marks close values as `corroborates` and shows both page quotes.

### 2. Genuine contradiction

When two sources describe the same subject and metric, cover the same period and unit, but contain materially different values, the result is `contradicts`. The result includes a confidence score, both page numbers, and the exact quotes used by the comparison.

### 3. Apparent contradiction explained by context

A value difference with a detected period or unit difference is `contextualizes`, not `contradicts`. For example, FY 2022 versus FY 2024 or crore versus million are represented in the fact metadata and included in the explanation. This is a deliberately conservative choice: the system does not collapse time-varying facts into one “truth.”

### 4. Extraction/reasoning failure

The baseline extractor intentionally does not claim to understand every table, scanned page, footnote, or compound sentence. A table where the row label is separated from its value can produce no fact or an over-broad candidate. That failure remains visible through the document/fact counts instead of being silently invented. The next improvement is layout-aware table extraction plus OCR fallback, followed by LLM structured extraction only for low-confidence candidates.

The checked-in evaluator makes this concrete rather than leaving it as prose:

```text
PASS | corroboration
PASS | contradiction
PASS | contextual difference
PASS | extraction abstention
4/4 behavioral cases passed
```

## Architecture

```text
PDF upload
  -> PyMuPDF page extraction
  -> page-aware overlapping chunks + metadata
  -> retrieval index + structured fact extraction
  -> normalized Fact + mandatory Evidence records
  -> entity graph + SQLAlchemy repository (PostgreSQL / SQLite local mode)
  -> deterministic resolution with optional LLM ambiguity support
  -> Flask REST API + evidence review UI + stdio MCP
```

Important decisions:

- **Evidence is mandatory**: every stored fact includes document id, filename, page number, quote, and character offsets where available.
- **Context beats forced merging**: time, unit, and scope are explicit metadata, and unresolved claims are not presented as settled truth.
- **Incremental processing**: each upload is processed independently; existing facts remain and relationships are recomputed against the expanded layer.
- **Provider independence**: the core can run offline. A paid LLM is not required to evaluate the submission.
- **RAG boundary**: retrieval returns ranked source context; it never independently labels claims as contradictory.
- **Controlled verification**: the generic API caller only permits HTTPS domains explicitly listed in `VERIFICATION_ALLOWED_DOMAINS`, limits response size, and is never required for core analysis.
- **Postgres-ready, SQLite-friendly**: Postgres is the deployment database; SQLite is a zero-setup local fallback using the same SQLAlchemy repository.

## AI tools used

GitHub Copilot was used for scaffolding, implementation iteration, and test-driven debugging. The extraction and comparison rules are local code, and the README calls out where the baseline is intentionally incomplete.

## Limitations and next steps

- The baseline parser is sentence-oriented and does not yet extract complex tables or scanned PDFs; add OCR and layout-aware table regions next.
- Subject matching is intentionally simple; add an entity-resolution index with aliases and embeddings for larger corpora.
- Pairwise comparison is adequate for a prototype but should use graph-aware candidate retrieval for thousands of facts.
- The optional LLM adapter currently processes chunks synchronously; production ingestion should move it to a durable background queue with retry and cost accounting.
- Add authentication, upload limits, background jobs, migrations, and object storage before production use.

## Additional notes

The app does not hard-code Delhivery or macroeconomic schemas. The starter PDFs are used only as input data. No credentials or external API calls are required for the core demo; external verification and LLM extraction are opt-in.

## Assignment requirement coverage

| Requirement | Status | Evidence in project |
|---|---|---|
| Upload new PDFs through a UI/API | Implemented | Flask upload route and drag/drop UI |
| Extract numerical facts | Implemented | PyMuPDF plus conservative normalized extractor |
| Extract semantic facts | Partial | LLM mode supports structured semantic claims; local fallback abstains when wording is ambiguous |
| Link every fact to source evidence | Implemented | Document, page, quote, offsets, and evidence endpoints |
| Corroborate across documents | Implemented with confidence limits | Relationship engine and corroboration endpoint |
| Detect contradictions | Implemented with confidence limits | Relationship engine and contradiction endpoint |
| Explain contextual differences | Implemented | Period/unit context is preserved and takes precedence over numeric similarity |
| Show an extraction/reasoning failure | Implemented | Evaluator includes extraction abstention |
| Generalize beyond starter filenames/schemas | Implemented | No dataset-specific branches or hard-coded facts |
| Add documents incrementally | Implemented | Each upload persists chunks/facts and recomputes derived relationships |
| Demo video and repository link | Not yet supplied | Must be added before submission |

The important qualification is that the no-credential extractor is intentionally conservative. It is better to abstain from a table or ambiguous semantic sentence than to create an unsupported claim. Enable the structured LLM mode for higher semantic recall, then review its evidence and confidence rather than treating it as ground truth.

## Why this should stand out

This project is optimized for the failure mode Superjoin actually cares about: a banker needs to know not only what the system found, but why it believes it, where it came from, and when two sources should not be merged. The demo therefore emphasizes evidence quotes, abstention, measured relationship cases, confidence, and explicit boundaries between retrieval and judgment. It avoids presenting a generic chat interface as intelligence.
