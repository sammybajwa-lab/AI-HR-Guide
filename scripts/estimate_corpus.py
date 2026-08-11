from __future__ import annotations

import json
import math
import re
from pathlib import Path

from app.settings import settings
from core.policy_loader import iter_supported_files


def word_count(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".html", ".htm"}:
        text = re.sub(r"<[^>]+>", " ", text)
    return len(re.findall(r"\b[\w'-]+\b", text))


if __name__ == "__main__":
    files = []
    total_words = 0
    for path in iter_supported_files(settings.corpus_dir):
        words = word_count(path)
        total_words += words
        files.append({"file": path.name, "words": words})
    # Policy documents contain headings, bullets, tables and white space; 325 words/page
    # is used only as a transparent planning estimate, not as a claim about rendered PDFs.
    manifest = {
        "document_count": len(files),
        "total_words": total_words,
        "planning_words_per_page": 325,
        "estimated_pages": math.ceil(total_words / 325),
        "files": files,
    }
    out = settings.corpus_dir / "corpus_manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
