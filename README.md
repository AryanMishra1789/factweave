# Factweave

Factweave extracts facts from PDFs, links each fact to its source passage, and compares related facts across documents.

It is designed for cases where two documents may:

- support the same fact;
- state different values;
- describe different periods, units, or scopes; or
- contain information that the extractor cannot safely interpret.

## Run locally

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:DATABASE_URL = "sqlite:///D:/Superjoin Assignment/.factweave/factweave.db"
flask --app app.main run --debug
```

Open http://127.0.0.1:5000.

To process the supplied PDFs:

```powershell
python scripts/seed_starter_data.py
```

The full graph-backed stack uses PostgreSQL and Neo4j:

```powershell
docker compose up --build
```

This starts the web app on http://127.0.0.1:8000, PostgreSQL for structured records, and Neo4j Browser on http://127.0.0.1:7474. Upload processing requires Neo4j because every fact and relationship is written to the graph.

## What it does

1. Extracts page text from uploaded PDFs with PyMuPDF.
2. Splits the text into page-aware chunks.
3. Retrieves relevant chunks using a local BM25-style search.
4. Extracts normalized facts with subject, predicate, value, unit, period, confidence, and evidence.
5. Compares facts from different documents.
6. Classifies relationships as `corroborates`, `contradicts`, or `contextualizes`.
7. Shows the result and source quotes in the UI.

The semantic extraction path supports an OpenAI-compatible structured extraction adapter. The deterministic extractor remains available as a local fallback for clear numeric claims and provider failures. Enable the LLM path with:

```powershell
$env:FACTWEAVE_EXTRACTION_MODE = "llm"
$env:OPENAI_API_KEY = "your-key"
```

## API

- `POST /api/documents` uploads a PDF.
- `GET /api/layer` returns documents, chunks, facts, entities, and relationships.
- `GET /api/search?q=revenue` searches grounded source passages.
- `GET /api/facts/<id>` returns a fact and its evidence.
- `GET /api/graph` returns the Neo4j graph snapshot.
- `GET /api/mcp/find-contradictions` returns contradiction findings.
- `POST /api/verify` optionally checks an allowlisted external HTTPS source.

An optional stdio MCP adapter is available in `app/mcp_server.py`.

For the system structure, see [Architecture.md](Architecture.md). For the technology choices and trade-offs, see [DECISIONS.md](DECISIONS.md).

## Approach and trade-offs

The pipeline separates retrieval from reasoning. PDF text is chunked and retrieved, facts are extracted with evidence, and a resolution layer compares values, units, periods, and scope. Neo4j stores the document-to-evidence-to-fact graph, while PostgreSQL stores structured application records.

The detailed technology decisions are documented in [DECISIONS.md](DECISIONS.md). The main trade-offs are using lexical retrieval for transparent local execution, an LLM-assisted extraction path with a deterministic fallback, and separate PostgreSQL and Neo4j stores so graph traversal does not replace the structured evidence store.

## Required cases

The UI displays evidence and reasoning for relationship findings.

- **Corroboration:** close values or equivalent claims from separate documents.
- **Contradiction:** materially different values for the same apparent claim without qualifying context.
- **Contextual difference:** values separated by a detected period or unit difference.
- **Extraction failure:** ambiguous table-like text is rejected rather than turned into an unsupported fact.

Run the behavioral check with:

```powershell
python scripts/evaluate.py
```

## Limitations and next steps

The local extractor works best with text-based PDF prose. Complex tables, scanned pages, and difficult semantic claims may be skipped. The current entity matching and relationship evaluation are suitable for a prototype, but need a larger labeled dataset before production use.

Next steps are OCR and layout-aware table extraction, stronger entity resolution, background processing for large PDFs, database migrations, object storage, and evaluation against labeled facts from the starter documents.

## Demo

The demo should show a PDF upload, extracted facts with page evidence, and one example each of corroboration, contradiction, contextual difference, and extraction abstention.

Demo video: https://drive.google.com/drive/folders/1S1CIjFzm_3YzcKy0OYeSpBSZOuWo0ajh?usp=sharing

## AI tools used

GitHub Copilot was used for implementation, debugging, and documentation. The core extraction and relationship rules are implemented in the repository and can run without an external model.

## Project links

- Repository: https://github.com/AryanMishra1789/factweave
