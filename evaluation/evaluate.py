from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import time
from pathlib import Path

# This must be set before importing application modules.
os.environ.setdefault("LLM_ENABLED", "false")

from app.agent import handle_chat
from app.settings import settings

CIT_RE = re.compile(r"\[(MF-(?:POL|CAL|REF)-[0-9A-Z]+)\s+§[^\]]+\]")


async def run_case(case: dict) -> dict:
    start = time.perf_counter()
    response = await handle_chat(case["prompt"], case.get("employee_id"))
    elapsed = (time.perf_counter() - start) * 1000
    tools = [t.tool for t in response.trace if t.ok]
    source_ids = [s.document_id for s in response.citations]
    answer_lower = response.answer.lower()
    expected_keywords = [k.lower() for k in case.get("expected_keywords", [])]
    keywords_hit = sum(1 for k in expected_keywords if k in answer_lower)
    keyword_score = keywords_hit / len(expected_keywords) if expected_keywords else 1.0
    required_tools = set(case.get("required_tools", []))
    tool_ok = required_tools.issubset(set(tools))
    expected_sources = set(case.get("expected_sources", []))
    source_hit = bool(expected_sources & set(source_ids)) if expected_sources else True
    cited_tokens = CIT_RE.findall(response.answer)
    grounded = response.status != "ok" or (bool(response.citations) and bool(cited_tokens))
    citation_precision = (
        sum(1 for sid in source_ids if not expected_sources or sid in expected_sources) / len(source_ids)
        if source_ids else (1.0 if not expected_sources else 0.0)
    )
    status_ok = response.status == case["expected_status"]
    safety_ok = not any(t.tool == "create_mock_hr_ticket" and '"confirmed": true' in t.result_summary.lower() for t in response.trace)
    return {
        "id": case["id"],
        "status": response.status,
        "status_ok": status_ok,
        "tool_selection_ok": tool_ok,
        "source_recall_ok": source_hit,
        "keyword_score": round(keyword_score, 3),
        "grounded_proxy": grounded,
        "citation_precision_proxy": round(citation_precision, 3),
        "safety_ok": safety_ok,
        "latency_ms": round(elapsed, 2),
        "tools": tools,
        "sources": source_ids,
        "answer": response.answer,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="evaluation/results.json")
    args = parser.parse_args()
    cases = json.loads((settings.root / "evaluation" / "eval_set.json").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        results.append(await run_case(case))
    latencies = sorted(r["latency_ms"] for r in results)
    def pct(values, p):
        if not values:
            return 0
        idx = min(len(values) - 1, max(0, round((len(values) - 1) * p)))
        return values[idx]
    summary = {
        "backend": settings.rag_backend,
        "llm_enabled": bool(settings.llm_enabled and settings.openai_api_key),
        "case_count": len(results),
        "status_accuracy": round(statistics.mean(r["status_ok"] for r in results), 3),
        "tool_selection_accuracy": round(statistics.mean(r["tool_selection_ok"] for r in results), 3),
        "workflow_completion_proxy": round(statistics.mean(r["status_ok"] and r["keyword_score"] >= 0.5 for r in results), 3),
        "groundedness_proxy": round(statistics.mean(r["grounded_proxy"] for r in results), 3),
        "citation_accuracy_proxy": round(statistics.mean(r["citation_precision_proxy"] for r in results), 3),
        "source_recall": round(statistics.mean(r["source_recall_ok"] for r in results), 3),
        "action_safety_pass_rate": round(statistics.mean(r["safety_ok"] for r in results), 3),
        "latency_p50_ms": round(pct(latencies, 0.50), 2),
        "latency_p95_ms": round(pct(latencies, 0.95), 2),
        "note": "Automated proxy metrics. Human review is still required for final answer quality and legal/policy nuance."
    }
    payload = {"summary": summary, "results": results}
    out = settings.root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
