from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from core.tool_impl import (
    check_policy_compliance_impl,
    check_pto_balance_impl,
    create_mock_hr_ticket_impl,
    draft_hr_email_impl,
    get_policy_section_impl,
    lookup_benefits_status_impl,
    lookup_employee_profile_impl,
    search_policy_documents_impl,
)

mcp = MCPServer("morrowfen-people-ops")


@mcp.tool()
def search_policy_documents(query: str, top_k: int = 4, document_id: str | None = None) -> dict[str, Any]:
    """Search the controlled Morrowfen policy corpus and return grounded policy evidence."""
    return search_policy_documents_impl(query, top_k, document_id)


@mcp.tool()
def get_policy_section(document_id: str, section: str) -> dict[str, Any]:
    """Retrieve the best matching section from one controlled policy document."""
    return get_policy_section_impl(document_id, section)


@mcp.tool()
def lookup_employee_profile(employee_id: str) -> dict[str, Any]:
    """Look up a synthetic employee profile by employee ID."""
    return lookup_employee_profile_impl(employee_id)


@mcp.tool()
def check_pto_balance(employee_id: str) -> dict[str, Any]:
    """Return the synthetic PTO balance for an employee."""
    return check_pto_balance_impl(employee_id)


@mcp.tool()
def lookup_benefits_status(employee_id: str) -> dict[str, Any]:
    """Return synthetic health-and-welfare eligibility/election status for an employee."""
    return lookup_benefits_status_impl(employee_id)


@mcp.tool()
def check_policy_compliance(
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
    """Apply deterministic policy checks for remote work, PTO, or expense scenarios using synthetic data."""
    return check_policy_compliance_impl(
        employee_id, scenario, destination, working_days, international, requested_hours, item_type, amount, preapproved
    )


@mcp.tool()
def create_mock_hr_ticket(employee_id: str, issue_type: str, summary: str, confirmed: bool = False) -> dict[str, Any]:
    """Preview or create a synthetic HR ticket. No write occurs unless confirmed is true."""
    return create_mock_hr_ticket_impl(employee_id, issue_type, summary, confirmed)


@mcp.tool()
def draft_hr_email(employee_id: str, purpose: str, details: str) -> dict[str, Any]:
    """Draft, but do not send, a short HR or manager email using synthetic employee data."""
    return draft_hr_email_impl(employee_id, purpose, details)


if __name__ == "__main__":
    mcp.run(transport="stdio")
