from __future__ import annotations

import inspect
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from app.settings import settings
from core.tool_impl import TOOL_IMPLS


def _result_to_python(result: Any) -> Any:
    for attr in ("structured_content", "structuredContent"):
        value = getattr(result, attr, None)
        if value:
            if isinstance(value, dict) and set(value.keys()) == {"result"}:
                return value["result"]
            return value
    content = getattr(result, "content", None) or []
    for part in content:
        text = getattr(part, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"text": text}
    return {"raw": str(result)}


class MCPToolSession:
    def __init__(self, session: Any = None, local: bool = False):
        self.session = session
        self.local = local

    async def list_tools(self) -> list[str]:
        if self.local:
            return list(TOOL_IMPLS)
        result = await self.session.list_tools()
        return [tool.name for tool in result.tools]

    async def call(self, name: str, arguments: dict[str, Any]) -> tuple[Any, float]:
        start = time.perf_counter()
        if self.local:
            fn = TOOL_IMPLS[name]
            result = fn(**arguments)
            if inspect.isawaitable(result):
                result = await result
        else:
            wire = await self.session.call_tool(name, arguments=arguments)
            result = _result_to_python(wire)
        elapsed = (time.perf_counter() - start) * 1000
        return result, elapsed


@asynccontextmanager
async def open_mcp_session() -> AsyncIterator[MCPToolSession]:
    """Use stdio MCP in normal operation; local dispatch exists only for offline CI-style analysis."""
    if settings.mcp_transport == "local":
        yield MCPToolSession(local=True)
        return

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = os.environ.copy()
    env["PYTHONPATH"] = str(settings.root) + os.pathsep + env.get("PYTHONPATH", "")
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp.server"],
        env=env,
        cwd=str(settings.root),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield MCPToolSession(session=session)
