from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from flask import Flask, jsonify, request, send_from_directory
from .config import UPLOAD_DIR
from .config import VERIFICATION_ALLOWED_DOMAINS
from .models import Document, KnowledgeLayer
from .pipeline import process_pdf
from .retrieval import retrieve
from .store import load_layer
from .verifier import VerificationError, verify_url

app = Flask(__name__, static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/health")
def health():
    return jsonify(status="ok", service="factweave")


@app.get("/api/layer")
def layer():
    documents, chunks, entities, facts, relationships = load_layer()
    return jsonify(KnowledgeLayer(documents=documents, chunks=chunks, entities=entities, facts=facts, relationships=relationships).model_dump(mode="json"))


@app.post("/api/documents")
def upload_document():
    file = request.files.get("file")
    if not file or not file.filename or not file.filename.lower().endswith(".pdf"):
        return jsonify(detail="Only PDF files are supported"), 400
    safe_filename = Path(file.filename).name
    document = Document(id=uuid4().hex[:12], filename=safe_filename, pages=0, uploaded_at=datetime.now(timezone.utc), status="processing")
    destination = UPLOAD_DIR / f"{document.id}.pdf"
    file.save(destination)
    try:
        process_pdf(document, destination)
    except Exception as error:
        document.status = "failed"
        return jsonify(detail=f"Could not process PDF: {error}"), 422
    return jsonify(document.model_dump(mode="json"))


@app.get("/api/mcp/tools")
def mcp_tools():
    return jsonify(tools=["search_facts", "get_fact", "find_contradictions", "find_corroborations", "get_evidence", "verify_external_source"])


@app.get("/api/facts/<fact_id>")
def get_fact(fact_id: str):
    _, _, _, facts, _ = load_layer()
    fact = next((item for item in facts if item.id == fact_id), None)
    if not fact:
        return jsonify(detail="Fact not found"), 404
    return jsonify(fact.model_dump(mode="json"))


@app.get("/api/facts/<fact_id>/evidence")
def get_evidence(fact_id: str):
    _, _, _, facts, _ = load_layer()
    fact = next((item for item in facts if item.id == fact_id), None)
    if not fact:
        return jsonify(detail="Fact not found"), 404
    return jsonify([item.model_dump(mode="json") for item in fact.evidence])


@app.get("/api/search")
def search():
    query = request.args.get("q", "").strip()
    limit = min(max(request.args.get("limit", 8, type=int), 1), 25)
    _, chunks, _, facts, _ = load_layer()
    results = [{"chunk": chunk.model_dump(mode="json"), "score": score} for chunk, score in retrieve(chunks, query, limit)]
    matching_facts = [fact.model_dump(mode="json") for fact in facts if query.lower() in f"{fact.subject} {fact.predicate} {fact.object}".lower()][:limit]
    return jsonify(query=query, results=results, matching_facts=matching_facts)


@app.get("/api/graph")
def graph():
    _, _, entities, facts, relationships = load_layer()
    return jsonify({"entities": [entity.model_dump(mode="json") for entity in entities], "facts": [fact.model_dump(mode="json") for fact in facts], "relationships": [item.model_dump(mode="json") for item in relationships]})


@app.get("/api/mcp/find-contradictions")
def mcp_contradictions():
    _, _, _, facts, relationships = load_layer()
    by_id = {fact.id: fact for fact in facts}
    return jsonify([{"relationship": item.model_dump(mode="json"), "facts": [by_id[item.source_fact_id].model_dump(mode="json"), by_id[item.target_fact_id].model_dump(mode="json")]} for item in relationships if item.relation == "contradicts"])


@app.get("/api/mcp/find-corroborations")
def mcp_corroborations():
    _, _, _, facts, relationships = load_layer()
    by_id = {fact.id: fact for fact in facts}
    return jsonify([{"relationship": item.model_dump(mode="json"), "facts": [by_id[item.source_fact_id].model_dump(mode="json"), by_id[item.target_fact_id].model_dump(mode="json")]} for item in relationships if item.relation == "corroborates"])


@app.post("/api/verify")
def verify_external_source():
    payload = request.get_json(silent=True) or {}
    try:
        result = verify_url(str(payload.get("url", "")), VERIFICATION_ALLOWED_DOMAINS)
    except VerificationError as error:
        return jsonify(detail=str(error)), 400
    return jsonify(result.model_dump(mode="json"))
