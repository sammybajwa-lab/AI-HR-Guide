from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.agent import handle_chat
from app.mcp_client import open_mcp_session
from app.models import ChatRequest, ChatResponse
from app.settings import settings

app = FastAPI(title=settings.app_name, version="1.0.0")
app.mount("/static", StaticFiles(directory=settings.root / "app" / "static"), name="static")
templates = Jinja2Templates(directory=settings.root / "app" / "templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"app_name": settings.app_name})


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    return await handle_chat(payload.message, payload.employee_id, payload.confirm_action)


@app.get("/health")
async def health():
    mcp_status = "unavailable"
    tool_count = 0
    try:
        async with asyncio.timeout(8):
            async with open_mcp_session() as session:
                tools = await session.list_tools()
                tool_count = len(tools)
                mcp_status = "ok"
    except Exception:
        pass
    return {
        "status": "ok" if mcp_status == "ok" else "degraded",
        "app": settings.app_name,
        "mcp": mcp_status,
        "mcp_tool_count": tool_count,
        "rag_backend": settings.rag_backend,
        "llm_enabled": bool(settings.llm_enabled and settings.openai_api_key),
    }


@app.get("/demo/scenarios")
async def demo_scenarios():
    return {
        "scenarios": [
            {
                "name": "International remote-work review",
                "employee_id": "E104",
                "prompt": "E104 wants to work from France for six weeks, Monday-Friday. Can she do it?",
            },
            {
                "name": "PTO balance and approval",
                "employee_id": "E102",
                "prompt": "E102 wants to use 24 hours of PTO. Does the balance support it, and what approval is still needed?",
            },
        ]
    }
