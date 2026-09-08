"""Small, reproducible behavioral evaluation for the assignment demo."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import Evidence, Fact
from app.extractor import extract_facts
from app.relations import compare_facts


def fact(identifier: str, document: str, value: str, number: float, period: str | None = "FY 2024") -> Fact:
    return Fact(id=identifier, subject="Revenue", predicate="was", object=value, fact_type="numeric", normalized_value=number, unit="crore", period=period, confidence=0.9, evidence=[Evidence(document_id=document, document_name=f"{document}.pdf", page_number=1, quote=f"Revenue was {value}.")])


cases = {
    "corroboration": (fact("a", "a", "120 crore", 120), fact("b", "b", "125 crore", 125), "corroborates"),
    "contradiction": (fact("c", "c", "120 crore", 120), fact("d", "d", "180 crore", 180), "contradicts"),
    "contextual difference": (fact("e", "e", "120 crore", 120, "FY 2023"), fact("f", "f", "180 crore", 180, "FY 2024"), "contextualizes"),
}

passed = 0
for name, (left, right, expected) in cases.items():
    relationships = compare_facts([left, right])
    actual = relationships[0].relation if relationships else "none"
    ok = actual == expected
    passed += int(ok)
    print(f"{'PASS' if ok else 'FAIL'} | {name} | expected={expected} actual={actual}")

unsupported_table = "Metric | FY2024 | FY2023\nRevenue | 120 | 110"
abstained = not extract_facts("table", "table.pdf", [(4, unsupported_table)])
passed += int(abstained)
print(f"{'PASS' if abstained else 'FAIL'} | extraction abstention | expected=no unsupported claim actual={'no claim' if abstained else 'claim emitted'}")

print(f"{passed}/{len(cases) + 1} behavioral cases passed")