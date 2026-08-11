import pytest

from app.mcp_client import open_mcp_session


@pytest.mark.asyncio
async def test_mcp_discovery_and_structured_tool_call():
    async with open_mcp_session() as session:
        tools = await session.list_tools()
        assert len(tools) >= 5
        assert "lookup_employee_profile" in tools
        result, _ = await session.call("lookup_employee_profile", {"employee_id": "E104"})
        assert result["found"] is True
        assert result["employee"]["employee_id"] == "E104"
