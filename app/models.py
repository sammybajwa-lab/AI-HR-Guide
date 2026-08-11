from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    employee_id: str | None = Field(default=None, pattern=r"^E\d{3}$")
    confirm_action: bool = False


class SourceRef(BaseModel):
    document_id: str
    title: str
    section: str
    snippet: str
    score: float | None = None

    @property
    def citation(self) -> str:
        return f"[{self.document_id} §{self.section}]"


class ToolTrace(BaseModel):
    tool: str
    arguments: dict[str, Any]
    result_summary: str
    ok: bool = True
    elapsed_ms: float | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[SourceRef] = []
    trace: list[ToolTrace] = []
    status: str = "ok"
    needs_confirmation: bool = False
    clarification_question: str | None = None
