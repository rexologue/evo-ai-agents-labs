"""A2A-обёртка для PurchaseMatcher."""
from __future__ import annotations

from typing import Any, AsyncGenerator, Dict

from .agent import PurchaseMatcherAgent


class PurchaseMatcherA2AWrapper:
    """Минимальная обёртка, совместимая с A2A протоколом."""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, agent: PurchaseMatcherAgent):
        self.agent = agent

    async def stream(self, query: str, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        result = await self.agent.handle(query, session_id)
        yield {
            "content": result.get("content"),
            "is_task_complete": result.get("is_task_complete", False),
            "require_user_input": result.get("require_user_input", False),
            "is_error": result.get("is_error", False),
            "is_event": False,
        }
