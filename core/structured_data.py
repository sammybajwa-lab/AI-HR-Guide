from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.settings import settings


def _read_json(name: str) -> Any:
    path = settings.mock_data_dir / name
    return json.loads(path.read_text(encoding="utf-8"))


def _by_employee(name: str, employee_id: str) -> dict[str, Any] | None:
    rows = _read_json(name)
    return next((row for row in rows if row.get("employee_id") == employee_id), None)


def lookup_employee(employee_id: str) -> dict[str, Any] | None:
    return _by_employee("employees.json", employee_id)


def pto_balance(employee_id: str) -> dict[str, Any] | None:
    return _by_employee("pto_balances.json", employee_id)


def benefits_status(employee_id: str) -> dict[str, Any] | None:
    return _by_employee("benefits.json", employee_id)


def ticket_path() -> Path:
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    runtime = settings.runtime_dir / "tickets.json"
    if not runtime.exists():
        runtime.write_text("[]\n", encoding="utf-8")
    return runtime


def create_ticket(employee_id: str, issue_type: str, summary: str) -> dict[str, Any]:
    path = ticket_path()
    rows = json.loads(path.read_text(encoding="utf-8"))
    ticket = {
        "ticket_id": f"MOCK-{len(rows) + 1:04d}",
        "employee_id": employee_id,
        "issue_type": issue_type,
        "summary": summary[:800],
        "status": "mock_created",
    }
    rows.append(ticket)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return ticket
