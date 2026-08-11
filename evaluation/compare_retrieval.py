from __future__ import annotations

import json
import os
from pathlib import Path

os.environ["RAG_BACKEND"] = "lexical"

from app.settings import settings
from core.rag import LexicalRAG


def retrieval_recall(k: int, cases: list[dict]) -> dict:
    rag = LexicalRAG()
    eligible = [c for c in cases if c.get("expected_sources")]
    hits = 0
    details = []
    for case in eligible:
        results = rag.search(case["prompt"], top_k=k)
        returned = {r["document_id"] for r in results}
        expected = set(case["expected_sources"])
        ok = bool(returned & expected)
        hits += int(ok)
        details.append({"id": case["id"], "hit": ok, "returned": sorted(returned), "expected": sorted(expected)})
    return {"k": k, "source_recall": round(hits / len(eligible), 3), "details": details}


if __name__ == "__main__":
    cases = json.loads((settings.root / "evaluation" / "eval_set.json").read_text(encoding="utf-8"))
    payload = {
        "comparison": "Lexical fallback retrieval k=3 versus k=5",
        "purpose": "Ablation harness showing how retrieval depth changes source recall. Run the same method with RAG_BACKEND=chroma before final submission for the production retrieval comparison.",
        "runs": [retrieval_recall(3, cases), retrieval_recall(5, cases)],
    }
    out = settings.root / "evaluation" / "ablation_results.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"runs": [{"k": r["k"], "source_recall": r["source_recall"]} for r in payload["runs"]]}, indent=2))
