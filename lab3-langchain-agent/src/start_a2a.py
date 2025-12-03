"""Точка входа для запуска LangChain агента через A2A протокол."""
import os
import logging
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
)
from phoenix.otel import register

from agent import create_langchain_agent
from a2a_wrapper import LangChainA2AWrapper
from agent_task_manager import LangChainAgentExecutor


# Настройка логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)
logger = logging.getLogger(__name__)


def main():
    """Основная функция запуска сервера."""
    try:
        # Настройка телеметрии Phoenix
        if os.getenv('ENABLE_PHOENIX', 'false').lower() == 'true':
            register(
                project_name=os.getenv("AGENT_NAME", "LangChain Agent"),
                endpoint=os.getenv("PHOENIX_ENDPOINT"),
                auto_instrument=True
            )
        
        # Создаем LangChain агента
        mcp_urls = os.getenv("MCP_URL")
        agent_executor = create_langchain_agent(mcp_urls)
        
        # Создаем A2A обертку
        agent_wrapper = LangChainA2AWrapper(agent_executor)
        
        # Создаем A2A executor
        agent_executor_a2a = LangChainAgentExecutor(agent_wrapper)
        
        # Настройка AgentCard
        capabilities = AgentCapabilities(streaming=True)
        agent_card = AgentCard(
            name=os.getenv('AGENT_NAME', 'LangChain Agent'),
            description=os.getenv('AGENT_DESCRIPTION', 'LangChain Agent для AI Agents платформы'),
            url=os.getenv('URL_AGENT'),
            version=os.getenv('AGENT_VERSION', '1.0.0'),
            default_input_modes=agent_wrapper.SUPPORTED_CONTENT_TYPES,
            default_output_modes=agent_wrapper.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[],
        )
        
        # Создаем request handler
        request_handler = DefaultRequestHandler(
            agent_executor=agent_executor_a2a,
            task_store=InMemoryTaskStore(),
        )
        
        # Создаем и запускаем сервер
        server = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler
        )
        
        import uvicorn
        port = int(os.getenv("PORT", 10000))
        logger.info(f"Starting LangChain Agent server on port {port}")
        uvicorn.run(server.build(), host='0.0.0.0', port=port)
        
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}', exc_info=True)
        exit(1)


if __name__ == '__main__':
    main()


