import hashlib
import re
from pathlib import Path
import pymupdf
from .models import Evidence, Fact

NUMBER = r"(?:INR|Rs\.?|USD|EUR|₹|%)?\s*[-+]?\d[\d,.]*(?:\s*(?:crore|million|billion|lakh|thousand|%))?"
DATE = r"(?:FY\s*\d{2,4}(?:-\d{2,4})?|Q[1-4]\s*FY\s*\d{2,4}|20\d{2}(?:-\d{2})?)"
GENERIC_SUBJECTS = {"at", "out", "stood", "which", "the", "and", "of", "in", "on", "by", "for", "to", "from", "a", "an"}


def read_pdf(path: Path) -> tuple[int, list[tuple[int, str]]]:
    pages: list[tuple[int, str]] = []
    with pymupdf.open(path) as pdf:
        for index, page in enumerate(pdf):
            text = " ".join(page.get_text("text").split())
            if text:
                pages.append((index + 1, text))
        return len(pdf), pages


def _fact_id(document_id: str, page: int, quote: str) -> str:
    return hashlib.sha1(f"{document_id}:{page}:{quote}".encode()).hexdigest()[:16]


def _evidence(document_id: str, filename: str, page: int, text: str, match: re.Match[str]) -> Evidence:
    start = max(0, match.start() - 180)
    end = min(len(text), match.end() + 180)
    quote = text[start:end].strip()
    return Evidence(document_id=document_id, document_name=filename, page_number=page, quote=quote, char_start=start, char_end=end, locator=f"Page {page}")


def extract_facts(document_id: str, filename: str, pages: list[tuple[int, str]]) -> list[Fact]:
    facts: list[Fact] = []
    # The baseline is deliberately conservative: it emits only claims anchored to a sentence with a number or a clear event verb.
    patterns = [
        re.compile(rf"(?P<subject>[A-Z][A-Za-z][A-Za-z &.'-]{{2,50}}?)\s+(?P<predicate>grew|increased|declined|decreased|stood at|was|were|reached|reported|recorded|rose|fell)\s+(?P<object>{NUMBER})", re.I),
        re.compile(rf"(?:the\s+)?(?P<subject>[A-Za-z][A-Za-z &.'-]{{2,50}}?)\s+(?P<predicate>of|at)\s+(?P<object>{NUMBER})", re.I),
        re.compile(rf"(?:the\s+)?(?P<subject>[A-Za-z][A-Za-z &.'-]{{2,50}}?)\s+(?:reported|recorded|reached)\s+(?:a\s+)?(?P<predicate>[A-Za-z][A-Za-z &.'-]{{2,40}}?)\s+(?:of|at)\s+(?P<object>{NUMBER})", re.I),
        re.compile(rf"(?P<subject>[A-Z][A-Za-z][A-Za-z &.'-]{{2,50}}?)\s+(?P<predicate>has|had|operates|employs|serves|covers)\s+(?P<object>{NUMBER})", re.I),
    ]
    for page, text in pages:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sentence in sentences:
            if len(sentence) < 25 or len(sentence) > 500:
                continue
            for pattern in patterns:
                match = pattern.search(sentence)
                if not match:
                    continue
                groups = match.groupdict()
                subject = groups["subject"].strip()
                if subject.lower().split()[0] in GENERIC_SUBJECTS or len(subject.split()) > 8:
                    continue
                object_value = groups.get("object") or "event"
                normalized: float | str | None = None
                number = re.search(r"[-+]?\d[\d,.]*", object_value)
                if number:
                    try:
                        normalized = float(number.group().replace(",", ""))
                    except ValueError:
                        normalized = object_value
                unit_match = re.search(r"(INR|Rs\.?|USD|EUR|₹|%|crore|million|billion|lakh|thousand)", object_value, re.I)
                period_match = re.search(DATE, sentence, re.I)
                evidence = _evidence(document_id, filename, page, sentence, match)
                facts.append(Fact(id=_fact_id(document_id, page, sentence), subject=subject, predicate=groups["predicate"].lower(), object=object_value.strip(), fact_type="numeric" if normalized is not None else "event", normalized_value=normalized, unit=unit_match.group(1) if unit_match else None, period=period_match.group(0) if period_match else None, confidence=0.72 if normalized is not None else 0.61, evidence=[evidence], method="rules"))
                break
    return facts
