from __future__ import annotations

from typing import Any

from core.structured_data import lookup_employee, pto_balance


def check_remote_work(employee_id: str, destination: str, working_days: int | None, international: bool) -> dict[str, Any]:
    employee = lookup_employee(employee_id)
    if not employee:
        return {"decision": "cannot_determine", "reasons": ["Employee record not found."], "required_approvals": [], "policy_references": ["MF-POL-201", "MF-POL-202"]}
    if working_days is None:
        return {
            "decision": "needs_clarification",
            "reasons": ["Expected working days are required for a location review."],
            "required_approvals": [],
            "policy_references": ["MF-POL-202"],
        }
    if international:
        approvals = ["People Operations", "Tax Operations", "Information Security"]
        if working_days > 20:
            return {
                "decision": "outside_standard_allowance",
                "reasons": [f"The request is {working_days} working days; the standard international allowance is up to 20 working days in a rolling 12-month period."],
                "required_approvals": approvals + ["formal assignment/transfer review"],
                "destination": destination,
                "policy_references": ["MF-POL-201", "MF-POL-202", "MF-POL-301"],
            }
        return {
            "decision": "review_required",
            "reasons": ["International remote work requires advance written cross-functional approval before work begins."],
            "required_approvals": approvals,
            "destination": destination,
            "policy_references": ["MF-POL-201", "MF-POL-202", "MF-POL-301"],
        }
    if working_days > 10:
        return {
            "decision": "review_required",
            "reasons": ["Temporary work in another U.S. state above 10 business days in a rolling 90-day period requires pre-travel review."],
            "required_approvals": ["People Operations", "Tax Operations"],
            "destination": destination,
            "policy_references": ["MF-POL-201", "MF-POL-202"],
        }
    return {
        "decision": "potentially_within_standard_threshold",
        "reasons": ["The duration is at or below the company-wide domestic review threshold, but location-specific or security rules can still require review."],
        "required_approvals": ["manager if team coverage changes"],
        "destination": destination,
        "policy_references": ["MF-POL-201", "MF-POL-202"],
    }


def check_pto(employee_id: str, requested_hours: float) -> dict[str, Any]:
    employee = lookup_employee(employee_id)
    balance = pto_balance(employee_id)
    if not employee or not balance:
        return {"decision": "cannot_determine", "reason": "Employee profile or PTO balance is missing.", "policy_references": ["MF-POL-101"]}
    if employee["employment_type"] in {"intern", "temporary"}:
        return {"decision": "not_eligible_company_pto", "reason": "The stored employment type does not accrue company PTO under the general policy.", "policy_references": ["MF-POL-101"]}
    available = float(balance["available_hours"])
    if requested_hours > available:
        return {"decision": "insufficient_balance", "available_hours": available, "requested_hours": requested_hours, "policy_references": ["MF-POL-101"]}
    return {
        "decision": "balance_sufficient_manager_approval_required",
        "available_hours": available,
        "requested_hours": requested_hours,
        "remaining_hours_if_approved": round(available - requested_hours, 2),
        "policy_references": ["MF-POL-101"],
    }


def check_expense(employee_id: str, item_type: str, amount: float, preapproved: bool = False) -> dict[str, Any]:
    employee = lookup_employee(employee_id)
    if not employee:
        return {"decision": "cannot_determine", "reason": "Employee record not found.", "policy_references": ["MF-POL-401"]}
    item = item_type.lower()
    if "laptop" in item:
        return {
            "decision": "not_standard_reimbursement",
            "reason": "Company laptops are provisioned through IT; personal purchase requires prior written IT and budget approval.",
            "required_approvals": ["IT Asset Management", "budget owner"],
            "policy_references": ["MF-POL-401", "MF-POL-402"],
        }
    if "chair" in item or "monitor" in item or "desk" in item:
        if employee["work_arrangement"] not in {"remote", "flexible"}:
            return {"decision": "not_eligible_standard_home_office_allowance", "reason": "Stored work arrangement does not meet the general home-office eligibility rule.", "policy_references": ["MF-POL-402"]}
        if amount > 350:
            return {"decision": "outside_standard_allowance", "reason": "The amount exceeds the one-time $350 home-office allowance.", "policy_references": ["MF-POL-402"]}
        if amount > 250 and not preapproved:
            return {"decision": "preapproval_required", "reason": "A single home-office item above $250 requires manager pre-approval.", "policy_references": ["MF-POL-402"]}
        return {"decision": "potentially_reimbursable", "reason": "The item can fit the general home-office rules if allowance remains and receipt/approval requirements are met.", "policy_references": ["MF-POL-401", "MF-POL-402"]}
    if amount >= 2500:
        return {"decision": "procurement_required", "reason": "Purchases of $2,500 or more must use Procurement unless an emergency exception is documented.", "policy_references": ["MF-POL-401"]}
    if amount >= 500:
        return {"decision": "budget_owner_approval_required", "reason": "Non-travel purchases from $500 through $2,499 require manager and budget-owner approval.", "policy_references": ["MF-POL-401"]}
    return {"decision": "manager_approval_required", "reason": "Routine business expenses below $500 require manager approval and must satisfy the general business-purpose and documentation rules.", "policy_references": ["MF-POL-401"]}
