import logging
from a2a.server.agent_execution import AgentExecutor as A2AAgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Task, TaskState, UnsupportedOperationError
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError
from a2a_wrapper import LangChainA2AWrapper

logger = logging.getLogger(__name__)


class LangChainAgentExecutor(A2AAgentExecutor):
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

        # 1️⃣ Пытаемся взять session_id из metadata, которое прислал клиент
        session_id: str | None = None
        try:
            metadata = getattr(context, "metadata", None) or {}
            if isinstance(metadata, dict):
                session_id = metadata.get("session_id")
        except Exception:
            session_id = None

        # 2️⃣ Если клиент не прислал session_id — fallback
        if not session_id:
            session_id = (
                getattr(context, "context_id", None)
                or (getattr(task, "context_id", None) if task else None)
                or (getattr(task, "id", None) if task else None)
                or "default"
            )

        logger.info(
            "LC-A2A execute: session_id=%s, context_id=%s, task_id=%s",
            session_id,
            getattr(context, "context_id", None),
            getattr(task, "id", None) if task else None,
        )

        # 3️⃣ Создаём задачу, если её ещё нет
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        # 4️⃣ Стримим ответ агента
        async for item in self.agent.stream(query, session_id):
            is_task_complete = item["is_task_complete"]
            require_user_input = item["require_user_input"]
            is_error = item["is_error"]
            is_event = item["is_event"]

            if is_error:
                await updater.update_status(
                    TaskState.failed,
                    new_agent_text_message(
                        item["content"], task.context_id, task.id
                    ),
                )
                break

            if is_event:
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(
                        item["content"], task.context_id, task.id
                    ),
                )
                continue

            if not is_task_complete and not require_user_input:
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(
                        item["content"], task.context_id, task.id
                    ),
                )
                continue

            if not is_task_complete and require_user_input:
                await updater.update_status(
                    TaskState.input_required,
                    new_agent_text_message(
                        item["content"], task.context_id, task.id
                    ),
                )
                break

            if is_task_complete and not require_user_input:
                await updater.update_status(
                    TaskState.completed,
                    new_agent_text_message(
                        item["content"], task.context_id, task.id
                    ),
                )
                break

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
