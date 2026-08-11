import pytest

from app.agent import handle_chat


@pytest.mark.asyncio
async def test_agent_asks_for_working_days_instead_of_guessing():
    response = await handle_chat("E104 wants to work from France for six weeks.", "E104")
    assert response.status == "needs_clarification"
    assert "working days" in (response.clarification_question or "").lower()


@pytest.mark.asyncio
async def test_pto_workflow_is_grounded_and_uses_tools():
    response = await handle_chat("E102 wants to use 24 hours of PTO.", "E102")
    assert response.status == "ok"
    assert "56" in response.answer
    assert any(c.document_id == "MF-POL-101" for c in response.citations)
    tool_names = {t.tool for t in response.trace if t.ok}
    assert {"check_pto_balance", "check_policy_compliance", "search_policy_documents"}.issubset(tool_names)
