from __future__ import annotations

import asyncio
import json

from app.agent import handle_chat


async def main() -> None:
    prompts = [
        ("E104", "E104 wants to work from France for six weeks, Monday-Friday. Can she do it?"),
        ("E102", "E102 wants to use 24 hours of PTO. Does the balance support it, and what approval is still needed?"),
    ]
    for employee_id, prompt in prompts:
        response = await handle_chat(prompt, employee_id)
        print("\n===", prompt)
        print(response.answer)
        print("tools:", [t.tool for t in response.trace])
        print("sources:", [c.document_id for c in response.citations])


if __name__ == "__main__":
    asyncio.run(main())
