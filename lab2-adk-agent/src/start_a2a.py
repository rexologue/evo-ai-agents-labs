import os

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
)
from dotenv import load_dotenv

from agent_task_manager import MyAgentExecutor
from phoenix.otel import register


# ==========================
# НАСТРОЙКА ЛОГГЕРА
# ==========================
import logging

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)
# ==========================

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        if os.getenv('ENABLE_PHOENIX', 'false').lower() == 'true':
            register(
                project_name=os.getenv("AGENT_NAME"),
                endpoint=os.getenv("PHOENIX_ENDPOINT"),
                auto_instrument=True
            )


        capabilities = AgentCapabilities(streaming=True)
        my_agent_executor = MyAgentExecutor()
        agent_card = AgentCard(
            name=os.getenv('AGENT_NAME', 'Work Agent'),
            description=os.getenv('AGENT_DESCRIPTION', 'This agent do work'),
            url=os.getenv('URL_AGENT'),
            version=os.getenv('AGENT_VERSION', '1.0.0'),
            default_input_modes=my_agent_executor.agent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=my_agent_executor.agent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[],
        )
        request_handler = DefaultRequestHandler(
            agent_executor=my_agent_executor,
            task_store=InMemoryTaskStore(),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )
        import uvicorn

        uvicorn.run(server.build(), host='0.0.0.0', port=int(os.getenv("PORT", 10000)))
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        exit(1)


if __name__ == '__main__':
    main()
