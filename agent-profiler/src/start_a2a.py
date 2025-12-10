"""Точка входа для запуска LangChain агента через A2A протокол."""
from config import get_settings, logger
settings = get_settings()

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
)

from agent import create_langchain_agent
from a2a_wrapper import LangChainA2AWrapper
from agent_task_manager import LangChainAgentExecutor

def main():
    """Основная функция запуска сервера."""
    try:
        # Создаем LangChain агента
        agent_executor = create_langchain_agent([settings.db_mcp_url, settings.codes_mcp_url])
        
        # Создаем A2A обертку
        agent_wrapper = LangChainA2AWrapper(agent_executor, auto_reset_on_complete=True)
        
        # Создаем A2A executor
        agent_executor_a2a = LangChainAgentExecutor(agent_wrapper)
        
        # Настройка AgentCard
        capabilities = AgentCapabilities(streaming=True)
        agent_card = AgentCard(
            name=settings.agent_name,
            description=settings.agent_desc,
            url=settings.agent_url,
            version=settings.agent_version,
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
        logger.info(f"Starting LangChain Agent server on port {settings.agent_port}")
        uvicorn.run(server.build(), host=settings.agent_host, port=settings.agent_port)
        
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}', exc_info=True)
        exit(1)


if __name__ == '__main__':
    main()