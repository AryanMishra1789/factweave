import re
from itertools import combinations
from .models import Fact, Relationship


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _same_subject(left: Fact, right: Fact) -> bool:
    ignored = {"the", "a", "an", "our", "your", "company", "summary", "industry", "figure", "fact", "report"}
    left_tokens = {token for token in re.findall(r"[a-z0-9]+", left.subject.lower()) if token not in ignored}
    right_tokens = {token for token in re.findall(r"[a-z0-9]+", right.subject.lower()) if token not in ignored}
    if not left_tokens or not right_tokens:
        return False
    if _key(left.subject) == _key(right.subject) and len(left_tokens) >= 1:
        return True
    shared = left_tokens & right_tokens
    return len(shared) >= 2 or (len(left_tokens) == 1 and len(right_tokens) == 1 and len(shared) == 1)


def _context(left: Fact, right: Fact) -> list[str]:
    context = []
    if left.period and right.period and left.period.lower() != right.period.lower():
        context.append(f"different periods ({left.period} vs {right.period})")
    if left.unit and right.unit and left.unit.lower() != right.unit.lower():
        context.append(f"different units ({left.unit} vs {right.unit})")
    return context


def compare_facts(facts: list[Fact]) -> list[Relationship]:
    relationships: list[Relationship] = []
    # Block candidates by normalized subject/predicate before comparing. This keeps
    # incremental ingestion close to linear for unrelated facts.
    buckets: dict[tuple[str, str], list[Fact]] = {}
    for fact in facts:
        subject = _key(fact.subject)
        predicate = _key(fact.predicate)
        buckets.setdefault((subject, predicate), []).append(fact)
        if predicate in {"was", "stoodat", "reported", "recorded"}:
            buckets.setdefault((subject, "value"), []).append(fact)
    candidates: set[tuple[str, str]] = set()
    for bucket in buckets.values():
        for left, right in combinations(bucket, 2):
            candidates.add(tuple(sorted((left.id, right.id))))
    by_id = {fact.id: fact for fact in facts}
    for left_id, right_id in candidates:
        left, right = by_id[left_id], by_id[right_id]
        if left.evidence[0].document_id == right.evidence[0].document_id or not _same_subject(left, right):
            continue
        generic_predicates = {"was", "stood at", "reported", "recorded"}
        if _key(left.predicate) != _key(right.predicate) and not ({left.predicate, right.predicate} <= generic_predicates):
            continue
        context = _context(left, right)
        relation = "unresolved"
        explanation = "The claims appear related, but the baseline extractor cannot establish equivalence confidently."
        confidence = 0.45
        if left.normalized_value is not None and right.normalized_value is not None:
            try:
                delta = abs(float(left.normalized_value) - float(right.normalized_value))
                scale = max(abs(float(left.normalized_value)), abs(float(right.normalized_value)), 1)
                if context:
                    relation, explanation, confidence = "contextualizes", "Values differ, but the evidence carries context that can explain the difference: " + ", ".join(context) + ".", 0.76
                elif delta / scale <= 0.08:
                    relation, explanation, confidence = "corroborates", "Values are close enough to support the same underlying claim.", 0.78
                else:
                    relation, explanation, confidence = "contradicts", "The same apparent claim has materially different values and no qualifying context was detected.", 0.70
            except (TypeError, ValueError):
                pass
        elif _key(left.object) == _key(right.object):
            relation, explanation, confidence = "corroborates", "Independent documents state the same normalized claim.", 0.73
        elif context:
            relation, explanation, confidence = "contextualizes", "The claims differ, but their periods, units, or source context are not the same.", 0.67
        if relation != "unresolved":
            relationships.append(Relationship(id=f"{left.id}-{right.id}", source_fact_id=left.id, target_fact_id=right.id, relation=relation, confidence=confidence, explanation=explanation, shared_context=context))
    return relationships
