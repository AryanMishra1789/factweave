import hashlib
import re
from .models import Entity, Fact


def canonical(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", value.lower())).strip()


def build_entities(facts: list[Fact]) -> list[Entity]:
    entities: dict[str, Entity] = {}
    for fact in facts:
        name = fact.subject.strip()
        key = canonical(name)
        if not key:
            continue
        entity_id = hashlib.sha1(key.encode()).hexdigest()[:16]
        if entity_id not in entities:
            entities[entity_id] = Entity(id=entity_id, canonical_name=name, aliases=[])
        if name not in entities[entity_id].aliases and name != entities[entity_id].canonical_name:
            entities[entity_id].aliases.append(name)
    return list(entities.values())
