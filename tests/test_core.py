from app.extractor import extract_facts
from app.graph import build_entities
from app.relations import compare_facts
from app.retrieval import retrieve
from app.verifier import VerificationError, verify_url
from app.models import Chunk


def test_extractor_keeps_page_evidence():
    facts = extract_facts("doc-a", "report.pdf", [(4, "The company reported revenue of INR 120 crore in FY 2024.")])
    assert facts
    assert facts[0].evidence[0].page_number == 4
    assert "revenue" in facts[0].subject.lower()


def test_material_difference_is_contradiction():
    a = extract_facts("a", "a.pdf", [(1, "Revenue was 120 crore in FY 2024.")])
    b = extract_facts("b", "b.pdf", [(2, "Revenue was 180 crore in FY 2024.")])
    relationships = compare_facts(a + b)
    assert any(r.relation == "contradicts" for r in relationships)


def test_retrieval_returns_relevant_chunk_first():
    chunks = [
        Chunk(id="1", document_id="a", document_name="a.pdf", page_number=1, text="Inflation fell to 4 percent in June.", char_start=0, char_end=38, token_count=7),
        Chunk(id="2", document_id="a", document_name="a.pdf", page_number=2, text="The logistics network expanded.", char_start=0, char_end=31, token_count=5),
    ]
    results = retrieve(chunks, "inflation June", limit=1)
    assert results[0][0].id == "1"


def test_graph_merges_exact_entity_aliases():
    facts = extract_facts("a", "a.pdf", [(1, "Delhivery was 120 crore in FY 2024.")])
    facts += extract_facts("b", "b.pdf", [(1, "Delhivery was 180 crore in FY 2024.")])
    assert len(build_entities(facts)) == 1


def test_verifier_rejects_untrusted_urls():
    try:
        verify_url("http://example.com", {"example.com"})
    except VerificationError:
        pass
    else:
        raise AssertionError("unsafe URL was accepted")
