"""AgentExecutor для интеграции LangChain агента с A2A."""
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    Task,
    TaskState,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError
from a2a_wrapper import LangChainA2AWrapper


class LangChainAgentExecutor(AgentExecutor):
    """AgentExecutor для LangChain агента."""

    def __init__(self, agent_wrapper: LangChainA2AWrapper):
        self.agent = agent_wrapper

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = context.get_user_input()
        task = context.current_task

        # Контекст чата должен привязываться к conversation/session id, а не к id новой задачи.
        # Иначе после подтверждения черновика история диалога теряется, и агент снова просит исходные данные.
        session_id = getattr(context, "context_id", None) or getattr(
            task, "context_id", None
        )

        # Создаем новую задачу, если её нет
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

            # если task только что создан, забираем context_id из него как запасной ключ сессии
            session_id = session_id or getattr(task, "context_id", None)

        # Финальный резерв: гарантируем наличие session_id
        session_id = session_id or getattr(task, "id", "default")
        
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        
        # Вызываем агента с streaming
        async for item in self.agent.stream(query, session_id):
            is_task_complete = item['is_task_complete']
            require_user_input = item['require_user_input']
            is_error = item['is_error']
            is_event = item['is_event']

            if is_error:
                await updater.update_status(
                    TaskState.failed,
                    new_agent_text_message(
                        item['content'], task.context_id, task.id
                    ),
                )
                break
            
            if is_event:
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(
                        item['content'], task.context_id, task.id
                    ),
                )
                continue
            
            if not is_task_complete and not require_user_input:
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(
                        item['content'], task.context_id, task.id
                    ),
                )
                continue

            if not is_task_complete and require_user_input:
                await updater.update_status(
                    TaskState.input_required,
                    new_agent_text_message(
                        item['content'], task.context_id, task.id
                    ),
                )
                break
            
            if is_task_complete and not require_user_input:
                await updater.update_status(
                    TaskState.completed,
                    new_agent_text_message(
                        item['content'], task.context_id, task.id
                    ),
                )
                break

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())


