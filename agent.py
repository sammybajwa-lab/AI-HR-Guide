from __future__ import annotations

import json
import re
from typing import Any

from app.llm import synthesize_grounded_answer
from app.mcp_client import MCPToolSession, open_mcp_session
from app.models import ChatResponse, SourceRef, ToolTrace
from app.settings import settings
from core.citations import citation_token

_EMP_RE = re.compile(r"\bE\d{3}\b", re.I)
_AMOUNT_RE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)")
_WORKING_DAYS_RE = re.compile(r"\b(\d{1,3})\s+(?:working|business)\s+days?\b", re.I)
_HOURS_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s+hours?\b", re.I)
_WEEKS_RE = re.compile(r"\b(\d+)\s+weeks?\b", re.I)

COUNTRY_HINTS = {
    "france", "spain", "italy", "germany", "india", "canada", "mexico", "japan", "uk", "united kingdom",
    "singapore", "australia", "brazil", "portugal", "ireland", "netherlands", "china", "south korea"
}
US_STATES = {
    "california", "texas", "florida", "new york", "massachusetts", "illinois", "washington", "new jersey",
    "colorado", "georgia", "arizona", "oregon", "virginia", "north carolina"
}


def _extract_employee_id(message: str, provided: str | None) -> str | None:
    if provided:
        return provided.upper()
    match = _EMP_RE.search(message)
    return match.group(0).upper() if match else None


def _intent(message: str) -> str:
    m = message.lower()
    if re.search(r"\bpto\b", m) or any(k in m for k in ["vacation", "time off", "take off"]):
        return "pto"
    if any(k in m for k in ["work remotely", "remote work", "work from", "another state", "another country", "abroad"]):
        return "remote_work"
    expense_operational = any(k in m for k in ["reimburse", "reimbursement", "chair", "laptop", "monitor", "travel cost"]) or bool(_AMOUNT_RE.search(message))
    if expense_operational:
        return "expense"
    if any(k in m for k in ["benefit", "medical plan", "dental", "vision", "health plan"]):
        return "benefits"
    if any(k in m for k in ["onboard", "onboarding", "new hire", "first day"]):
        return "onboarding"
    if any(k in m for k in ["harass", "retaliat", "threat", "discriminat", "workplace concern", "report my manager"]):
        return "hr_case"
    if any(k in m for k in ["stock price", "weather", "sports score", "recipe", "write code for"]):
        return "out_of_scope"
    return "policy_qna"


def _extract_location(message: str) -> tuple[str | None, bool | None]:
    lower = message.lower()
    for country in sorted(COUNTRY_HINTS, key=len, reverse=True):
        if country in lower:
            return country.title(), True
    for state in sorted(US_STATES, key=len, reverse=True):
        if state in lower:
            return state.title(), False
    match = re.search(r"(?:from|in)\s+([A-Z][A-Za-z .'-]{2,30})", message)
    if match:
        loc = match.group(1).strip().rstrip("?.!,")
        return loc, None
    return None, None


def _extract_working_days(message: str) -> int | None:
    match = _WORKING_DAYS_RE.search(message)
    if match:
        return int(match.group(1))
    weeks = _WEEKS_RE.search(message)
    lower = message.lower()
    week_count = int(weeks.group(1)) if weeks else None
    if week_count is None:
        word_match = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s+weeks?\b", lower)
        if word_match:
            week_count = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}[word_match.group(1)]
    if week_count is not None and any(phrase in lower for phrase in ["monday to friday", "monday-friday", "five days a week", "5 days a week"]):
        return week_count * 5
    return None


def _extract_requested_hours(message: str) -> float | None:
    match = _HOURS_RE.search(message)
    return float(match.group(1)) if match else None


def _extract_expense(message: str) -> tuple[str | None, float | None]:
    lower = message.lower()
    item = next((x for x in ["laptop", "home office chair", "chair", "monitor", "desk", "software subscription", "meal", "travel expense"] if x in lower), None)
    amt = _AMOUNT_RE.search(message)
    return item, float(amt.group(1)) if amt else None


def _source_refs(results: list[dict[str, Any]]) -> list[SourceRef]:
    seen: set[tuple[str, str]] = set()
    refs: list[SourceRef] = []
    for src in results:
        key = (src["document_id"], src["section"])
        if key in seen:
            continue
        seen.add(key)
        refs.append(
            SourceRef(
                document_id=src["document_id"],
                title=src["title"],
                section=src["section"],
                snippet=src.get("snippet") or src.get("text", "")[:500],
                score=src.get("score"),
            )
        )
    return refs


async def _call(session: MCPToolSession, trace: list[ToolTrace], name: str, args: dict[str, Any]) -> Any:
    try:
        result, elapsed = await session.call(name, args)
        summary = json.dumps(result, ensure_ascii=False, default=str)
        trace.append(ToolTrace(tool=name, arguments=args, result_summary=summary[:900], ok=True, elapsed_ms=round(elapsed, 2)))
        return result
    except Exception as exc:
        trace.append(ToolTrace(tool=name, arguments=args, result_summary=f"Tool error: {type(exc).__name__}", ok=False))
        raise


def _evidence_digest(question: str, sources: list[dict[str, Any]]) -> str:
    if not sources:
        return "I could not find enough policy evidence in the controlled corpus to answer that. Please route the question to People Operations."
    lines = []
    for src in sources[:3]:
        snippet = re.sub(r"\s+", " ", src.get("snippet") or src.get("text", "")).strip()
        if len(snippet) > 330:
            snippet = snippet[:327].rstrip() + "..."
        lines.append(f"- {snippet} {citation_token(src)}")
    return "Policy evidence found:\n" + "\n".join(lines)


async def handle_chat(message: str, employee_id: str | None = None, confirm_action: bool = False) -> ChatResponse:
    intent = _intent(message)
    employee_id = _extract_employee_id(message, employee_id)
    trace: list[ToolTrace] = []
    sources: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []

    if intent == "out_of_scope":
        return ChatResponse(
            answer="This desk is limited to the synthetic Morrowfen HR policy and operations corpus. I do not have grounded company evidence for that request.",
            status="out_of_scope",
        )

    try:
        async with open_mcp_session() as mcp:
            if intent == "pto":
                if not employee_id:
                    return ChatResponse(answer="I need the synthetic employee ID before I can check a PTO balance.", status="needs_clarification", clarification_question="What is the employee ID (for example, E102)?")
                hours = _extract_requested_hours(message)
                if hours is None:
                    return ChatResponse(answer="I can check this once the request is stated in hours. The policy does not let me assume every employee works eight-hour days.", status="needs_clarification", clarification_question="How many PTO hours are you requesting?")
                profile = await _call(mcp, trace, "lookup_employee_profile", {"employee_id": employee_id})
                balance = await _call(mcp, trace, "check_pto_balance", {"employee_id": employee_id})
                decision = await _call(mcp, trace, "check_policy_compliance", {"employee_id": employee_id, "scenario": "pto", "requested_hours": hours})
                policy = await _call(mcp, trace, "search_policy_documents", {"query": "PTO balance request timing manager approval consecutive days negative balance", "top_k": settings.rag_top_k, "document_id": "MF-POL-101"})
                sources = policy.get("results", [])
                facts = [profile, balance, decision]
                d = decision.get("decision")
                if d == "balance_sufficient_manager_approval_required":
                    fallback = (
                        f"The stored balance is {decision['available_hours']:.0f} hours. A {hours:g}-hour request would leave {decision['remaining_hours_if_approved']:.0f} hours. "
                        f"The balance is sufficient, but manager approval and the applicable notice window still apply. {citation_token(sources[0]) if sources else ''}"
                    ).strip()
                elif d == "insufficient_balance":
                    fallback = f"The stored balance is {decision['available_hours']:.0f} hours, which is below the {hours:g} hours requested. A negative balance needs People Operations approval; a manager cannot approve it alone. {citation_token(sources[0]) if sources else ''}".strip()
                else:
                    fallback = f"I cannot complete the PTO determination from the stored records. {citation_token(sources[0]) if sources else ''}".strip()
                answer = await synthesize_grounded_answer(message, sources, facts, fallback)

            elif intent == "remote_work":
                if not employee_id:
                    return ChatResponse(answer="I need the synthetic employee ID because work-location rules depend on the employee record.", status="needs_clarification", clarification_question="What is the employee ID?")
                destination, international = _extract_location(message)
                days = _extract_working_days(message)
                if not destination:
                    return ChatResponse(answer="The destination is required for a work-location review.", status="needs_clarification", clarification_question="Which state or country will the employee work from?")
                if international is None:
                    return ChatResponse(answer="I found a destination name but cannot safely tell whether it is domestic or international from the request.", status="needs_clarification", clarification_question="Is the destination outside the employee's country of employment?")
                if days is None:
                    return ChatResponse(answer="I need the expected number of working days. The policy uses working-day thresholds, so I will not convert calendar weeks without the work schedule.", status="needs_clarification", clarification_question="How many working days will be spent in that location?")
                profile = await _call(mcp, trace, "lookup_employee_profile", {"employee_id": employee_id})
                decision = await _call(mcp, trace, "check_policy_compliance", {"employee_id": employee_id, "scenario": "remote_work", "destination": destination, "working_days": days, "international": international})
                remote_query = (
                    "standard temporary international remote work 20 working days rolling 12 months formal assignment approval"
                    if international else
                    "temporary domestic remote work another state 10 business days rolling 90 days tax review"
                )
                policy = await _call(mcp, trace, "search_policy_documents", {"query": remote_query, "top_k": 6})
                sources = [s for s in policy.get("results", []) if s["document_id"] in {"MF-POL-201", "MF-POL-202", "MF-POL-301"}]
                facts = [profile, decision]
                if decision.get("decision") == "outside_standard_allowance":
                    threshold_source = next((s for s in sources if s["document_id"] == "MF-POL-201" and "international" in s["section"].lower()), None)
                    threshold_source = threshold_source or next((s for s in sources if "threshold" in s["section"].lower()), None) or (sources[0] if sources else None)
                    cite = citation_token(threshold_source) if threshold_source else ""
                    fallback = (
                        f"This request is outside the standard temporary international arrangement. The request is {days} working days, while the standard allowance is up to 20 working days in a rolling 12-month period; it needs formal assignment/transfer review and the required People Operations, Tax Operations, and Information Security approvals before work begins. "
                        f"{cite}"
                    ).strip()
                elif decision.get("decision") == "review_required":
                    fallback = (
                        f"The request requires pre-approval before work starts. Required reviewers in the stored rule are: {', '.join(decision.get('required_approvals', []))}. "
                        f"{citation_token(sources[0]) if sources else ''}"
                    ).strip()
                else:
                    fallback = _evidence_digest(message, sources)
                answer = await synthesize_grounded_answer(message, sources, facts, fallback)

            elif intent == "expense":
                if not employee_id:
                    return ChatResponse(answer="I need the synthetic employee ID because home-office eligibility can depend on the employee's work arrangement.", status="needs_clarification", clarification_question="What is the employee ID?")
                item, amount = _extract_expense(message)
                if not item or amount is None:
                    return ChatResponse(answer="I need both the item and the amount to apply the expense thresholds.", status="needs_clarification", clarification_question="What is the item and its amount in dollars?")
                profile = await _call(mcp, trace, "lookup_employee_profile", {"employee_id": employee_id})
                lower_message = message.lower()
                preapproved = ("pre-approved" in lower_message or "preapproved" in lower_message) and not ("not pre-approved" in lower_message or "not preapproved" in lower_message)
                decision = await _call(mcp, trace, "check_policy_compliance", {"employee_id": employee_id, "scenario": "expense", "item_type": item, "amount": amount, "preapproved": preapproved})
                policy = await _call(mcp, trace, "search_policy_documents", {"query": f"{item} reimbursement home office approval receipt expense", "top_k": 5})
                sources = [s for s in policy.get("results", []) if s["document_id"] in {"MF-POL-401", "MF-POL-402"}]
                facts = [profile, decision]
                fallback = f"Decision: {decision.get('decision', 'cannot_determine').replace('_', ' ')}. {decision.get('reason', '')} {citation_token(sources[0]) if sources else ''}".strip()
                answer = await synthesize_grounded_answer(message, sources, facts, fallback)

            elif intent == "benefits":
                policy = await _call(mcp, trace, "search_policy_documents", {"query": "health welfare benefits eligibility scheduled hours first day month following 30 days", "top_k": 4, "document_id": "MF-POL-501"})
                sources = policy.get("results", [])
                if employee_id:
                    profile = await _call(mcp, trace, "lookup_employee_profile", {"employee_id": employee_id})
                    benefit = await _call(mcp, trace, "lookup_benefits_status", {"employee_id": employee_id})
                    facts = [profile, benefit]
                    b = benefit.get("benefits") or {}
                    fallback = f"Stored benefits status for {employee_id}: {b.get('eligibility_status', 'not found')}; medical: {b.get('medical', 'not found')}; effective date: {b.get('effective_date') or 'not recorded'}. {citation_token(sources[0]) if sources else ''}".strip()
                else:
                    fallback = _evidence_digest(message, sources)
                answer = await synthesize_grounded_answer(message, sources, facts, fallback)

            elif intent == "onboarding":
                policy = await _call(mcp, trace, "search_policy_documents", {"query": "onboarding first day access security training equipment 30-day check", "top_k": 5, "document_id": "MF-POL-601"})
                sources = policy.get("results", [])
                if employee_id:
                    profile = await _call(mcp, trace, "lookup_employee_profile", {"employee_id": employee_id})
                    facts = [profile]
                    employee = profile.get("employee") or {}
                    training = employee.get("security_training_complete")
                    fallback = (
                        f"For {employee_id}, the stored profile shows work arrangement '{employee.get('work_arrangement', 'not recorded')}' and security training complete = {training}. "
                        f"Other onboarding steps are not marked complete unless a source record says so. {citation_token(sources[0]) if sources else ''}"
                    ).strip()
                else:
                    fallback = _evidence_digest(message, sources)
                answer = await synthesize_grounded_answer(message, sources, facts, fallback)

            elif intent == "hr_case":
                policy = await _call(mcp, trace, "search_policy_documents", {"query": "workplace conduct reporting retaliation escalation HR case privacy urgent threat", "top_k": 6})
                sources = [s for s in policy.get("results", []) if s["document_id"] in {"MF-POL-701", "MF-POL-703"}]
                lower = message.lower()
                urgent = any(k in lower for k in ["immediate threat", "threat of violence", "weapon", "in danger now"])
                fallback = (
                    "This should be escalated rather than decided by the assistant. "
                    + ("Because the description indicates immediate physical-safety risk, use local emergency procedures first, then report internally when safe. " if urgent else "People Operations, Legal, a manager not involved in the concern, or the confidential speak-up channel are available reporting routes. ")
                    + (citation_token(sources[0]) if sources else "")
                ).strip()
                if employee_id and ("create" in lower and "ticket" in lower or "case" in lower):
                    ticket = await _call(mcp, trace, "create_mock_hr_ticket", {"employee_id": employee_id, "issue_type": "workplace_conduct", "summary": message, "confirmed": confirm_action})
                    facts = [ticket]
                    if ticket.get("requires_confirmation"):
                        fallback += " I prepared a mock case preview, but nothing was written because confirmation is required."
                    elif ticket.get("created"):
                        fallback += f" Mock case {ticket['ticket']['ticket_id']} was written to synthetic runtime data only."
                answer = await synthesize_grounded_answer(message, sources, facts, fallback)

            else:
                query = message
                lower = message.lower()
                if ("stolen" in lower or "lost" in lower) and ("device" in lower or "computer" in lower):
                    query = "lost stolen company device security incident report immediately preserve evidence"
                elif "receipt" in lower and "expense" in lower:
                    query = "business expense itemized receipt threshold $25"
                elif "medical restriction" in lower or "workplace adjustment" in lower:
                    query = "workplace accommodation medical restriction interactive review adjustment"
                policy = await _call(mcp, trace, "search_policy_documents", {"query": query, "top_k": settings.rag_top_k})
                sources = policy.get("results", [])
                fallback = _evidence_digest(message, sources)
                answer = await synthesize_grounded_answer(message, sources, [], fallback)

    except Exception:
        return ChatResponse(
            answer="The HR tool layer is unavailable right now, so I cannot give a grounded policy answer. No action was taken.",
            trace=trace,
            status="tool_error",
        )

    return ChatResponse(answer=answer, citations=_source_refs(sources), trace=trace, status="ok")
