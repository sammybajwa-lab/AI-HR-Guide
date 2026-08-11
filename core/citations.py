from __future__ import annotations

import re
from typing import Iterable

_CITATION_RE = re.compile(r"\[(MF-(?:POL|CAL|REF)-[0-9A-Z]+)\s+§([^\]]+)\]")


def citation_token(source: dict) -> str:
    return f"[{source['document_id']} §{source['section']}]"


def validate_citations(answer: str, sources: Iterable[dict]) -> tuple[bool, list[str]]:
    allowed = {(s["document_id"], s["section"]) for s in sources}
    found = _CITATION_RE.findall(answer)
    unknown = [f"[{doc} §{sec}]" for doc, sec in found if (doc, sec) not in allowed]
    return bool(found) and not unknown, unknown
