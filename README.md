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

PostgreSQL is also supported:

```powershell
docker compose up --build
```

## What it does

1. Extracts page text from uploaded PDFs with PyMuPDF.
2. Splits the text into page-aware chunks.
3. Retrieves relevant chunks using a local BM25-style search.
4. Extracts normalized facts with subject, predicate, value, unit, period, confidence, and evidence.
5. Compares facts from different documents.
6. Classifies relationships as `corroborates`, `contradicts`, or `contextualizes`.
7. Shows the result and source quotes in the UI.

The default pipeline is local and does not require an LLM or API key. An optional OpenAI-compatible structured extraction adapter can be enabled with:

```powershell
$env:FACTWEAVE_EXTRACTION_MODE = "llm"
$env:OPENAI_API_KEY = "your-key"
```

## API

- `POST /api/documents` uploads a PDF.
- `GET /api/layer` returns documents, chunks, facts, entities, and relationships.
- `GET /api/search?q=revenue` searches grounded source passages.
- `GET /api/facts/<id>` returns a fact and its evidence.
- `GET /api/graph` returns entities and relationships.
- `GET /api/mcp/find-contradictions` returns contradiction findings.
- `POST /api/verify` optionally checks an allowlisted external HTTPS source.

An optional stdio MCP adapter is available in `app/mcp_server.py`.

For the system structure, see [Architecture.md](Architecture.md). For the technology choices and trade-offs, see [DECISIONS.md](DECISIONS.md).

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

## Project links

- Repository: https://github.com/AryanMishra1789/factweave
- Demo video: to be added
