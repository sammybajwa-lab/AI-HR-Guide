from __future__ import annotations

from typing import Any

from core.compliance import check_expense, check_pto, check_remote_work
from core.rag import get_rag
from core.structured_data import benefits_status, create_ticket, lookup_employee, pto_balance


def search_policy_documents_impl(query: str, top_k: int = 4, document_id: str | None = None) -> dict[str, Any]:
    top_k = max(1, min(int(top_k), 8))
    hits = get_rag().search(query=query, top_k=top_k, document_id=document_id)
    return {"query": query, "count": len(hits), "results": hits}


def get_policy_section_impl(document_id: str, section: str) -> dict[str, Any]:
    hit = get_rag().get_section(document_id=document_id, section_query=section)
    return {"found": hit is not None, "result": hit}


def lookup_employee_profile_impl(employee_id: str) -> dict[str, Any]:
    row = lookup_employee(employee_id)
    return {"found": row is not None, "employee": row}


def check_pto_balance_impl(employee_id: str) -> dict[str, Any]:
    row = pto_balance(employee_id)
    return {"found": row is not None, "pto": row}


def lookup_benefits_status_impl(employee_id: str) -> dict[str, Any]:
    row = benefits_status(employee_id)
    return {"found": row is not None, "benefits": row}


def check_policy_compliance_impl(
    employee_id: str,
    scenario: str,
    destination: str | None = None,
    working_days: int | None = None,
    international: bool | None = None,
    requested_hours: float | None = None,
    item_type: str | None = None,
    amount: float | None = None,
    preapproved: bool = False,
) -> dict[str, Any]:
    scenario = scenario.strip().lower()
    if scenario == "remote_work":
        if not destination or international is None:
            return {"decision": "needs_clarification", "reason": "destination and international flag are required"}
        return check_remote_work(employee_id, destination, working_days, bool(international))
    if scenario == "pto":
        if requested_hours is None:
            return {"decision": "needs_clarification", "reason": "requested_hours is required"}
        return check_pto(employee_id, float(requested_hours))
    if scenario == "expense":
        if not item_type or amount is None:
            return {"decision": "needs_clarification", "reason": "item_type and amount are required"}
        return check_expense(employee_id, item_type, float(amount), preapproved=preapproved)
    return {"decision": "unsupported_scenario", "supported": ["remote_work", "pto", "expense"]}


def create_mock_hr_ticket_impl(employee_id: str, issue_type: str, summary: str, confirmed: bool = False) -> dict[str, Any]:
    if not lookup_employee(employee_id):
        return {"created": False, "reason": "employee_not_found"}
    preview = {"employee_id": employee_id, "issue_type": issue_type, "summary": summary[:800]}
    if not confirmed:
        return {"created": False, "requires_confirmation": True, "preview": preview}
    ticket = create_ticket(employee_id, issue_type, summary)
    return {"created": True, "requires_confirmation": False, "ticket": ticket}


def draft_hr_email_impl(employee_id: str, purpose: str, details: str) -> dict[str, Any]:
    employee = lookup_employee(employee_id)
    if not employee:
        return {"drafted": False, "reason": "employee_not_found"}
    subject = f"{purpose.strip().title()} — {employee['name']} ({employee_id})"
    body = (
        f"Hello,\n\nI am writing regarding {purpose.strip().lower()} for {employee['name']} ({employee_id}). "
        f"{details.strip()}\n\nPlease review and let me know if anything else is needed.\n"
    )
    return {"drafted": True, "sent": False, "subject": subject, "body": body}


TOOL_IMPLS = {
    "search_policy_documents": search_policy_documents_impl,
    "get_policy_section": get_policy_section_impl,
    "lookup_employee_profile": lookup_employee_profile_impl,
    "check_pto_balance": check_pto_balance_impl,
    "lookup_benefits_status": lookup_benefits_status_impl,
    "check_policy_compliance": check_policy_compliance_impl,
    "create_mock_hr_ticket": create_mock_hr_ticket_impl,
    "draft_hr_email": draft_hr_email_impl,
}
