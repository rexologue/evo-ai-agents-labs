"""Точка входа для PurchaseMatcher агента."""
from __future__ import annotations

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard

from .agent import PurchaseMatcherAgent
from .agent_task_manager import PurchaseMatcherExecutor
from .a2a_wrapper import PurchaseMatcherA2AWrapper
from .config import get_settings, logger

settings = get_settings()


def main() -> None:
    try:
        agent = PurchaseMatcherAgent()
        wrapper = PurchaseMatcherA2AWrapper(agent)
        executor = PurchaseMatcherExecutor(wrapper)

        capabilities = AgentCapabilities(streaming=True)
        agent_card = AgentCard(
            name=settings.agent_name,
            description=settings.agent_desc,
            url=settings.agent_url,
            version=settings.agent_version,
            default_input_modes=wrapper.SUPPORTED_CONTENT_TYPES,
            default_output_modes=wrapper.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[],
        )

        handler = DefaultRequestHandler(
            agent_executor=executor,
            task_store=InMemoryTaskStore(),
        )

        server = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)
        logger.info(
            "Starting PurchaseMatcher agent on http://%s:%s", settings.agent_host, settings.agent_port
        )
        uvicorn.run(server.build(), host=settings.agent_host, port=settings.agent_port)
    except Exception:
        logger.exception("PurchaseMatcher failed to start")
        raise


if __name__ == "__main__":
    main()
