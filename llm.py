from __future__ import annotations

import json
from typing import Any

from app.settings import settings
from core.citations import citation_token, validate_citations


async def synthesize_grounded_answer(
    question: str,
    sources: list[dict[str, Any]],
    tool_facts: list[dict[str, Any]],
    fallback: str,
) -> str:
    """Use an LLM only when configured, then reject outputs with invalid citations."""
    if not settings.llm_enabled or not settings.openai_api_key:
        return fallback

    from openai import AsyncOpenAI

    client_kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        client_kwargs["base_url"] = settings.openai_base_url
    client = AsyncOpenAI(**client_kwargs)

    evidence = [
        {
            "citation": citation_token(src),
            "document_id": src["document_id"],
            "section": src["section"],
            "text": src.get("text") or src.get("snippet", ""),
        }
        for src in sources
    ]

    system = (
        "You write short internal HR answers for Morrowfen Systems. Use only the supplied policy evidence and "
        "structured tool facts. Do not add legal rules, dates, balances, approvals, or company practices that are not "
        "in the supplied material. Every sentence that states a policy rule must end with one of the exact citation "
        "tokens provided. If evidence is missing, say what is missing. Separate a practical next step from a policy fact. "
        "Do not claim that a mock action was actually sent or performed. Use plain workplace language, not marketing copy."
    )
    user = {
        "question": question,
        "policy_evidence": evidence,
        "structured_tool_facts": tool_facts,
        "allowed_citations": [e["citation"] for e in evidence],
    }

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
        )
        text = (response.choices[0].message.content or "").strip()
        valid, _ = validate_citations(text, sources)
        if not text or (sources and not valid):
            return fallback
        return text
    except Exception:
        return fallback
