"""Optional stdio MCP adapter over the same repository services used by Flask."""
import json
from .retrieval import retrieve
from .store import load_layer

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as error:  # pragma: no cover - optional runtime dependency
    raise SystemExit("Install the 'agent' extra to run the MCP server: pip install -e '.[agent]'") from error

mcp = FastMCP("factweave")


@mcp.tool()
def search_facts(query: str, limit: int = 8) -> str:
    """Retrieve evidence chunks and matching facts for a natural-language query."""
    _, chunks, _, facts, _ = load_layer()
    matches = retrieve(chunks, query, min(max(limit, 1), 20))
    return json.dumps({"chunks": [{"chunk": chunk.model_dump(mode="json"), "score": score} for chunk, score in matches], "facts": [fact.model_dump(mode="json") for fact in facts if query.lower() in f"{fact.subject} {fact.predicate} {fact.object}".lower()][:limit]})


@mcp.tool()
def find_contradictions() -> str:
    """Return contradiction relationships with their source facts and evidence."""
    _, _, _, facts, relationships = load_layer()
    by_id = {fact.id: fact for fact in facts}
    result = [{"relationship": item.model_dump(mode="json"), "facts": [by_id[item.source_fact_id].model_dump(mode="json"), by_id[item.target_fact_id].model_dump(mode="json")]} for item in relationships if item.relation == "contradicts"]
    return json.dumps(result)


if __name__ == "__main__":
    mcp.run()