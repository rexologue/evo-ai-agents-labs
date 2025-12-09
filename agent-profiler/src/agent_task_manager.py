from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Task, TaskState, UnsupportedOperationError
from a2a.utils import new_agent_text_message, new_task
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

        # 1) Гарантируем, что Task существует
        if not task:
            if not context.message:
                raise ServerError("No message in RequestContext")
            task = new_task(context.message)  # type: ignore[arg-type]
            await event_queue.enqueue_event(task)

        # 2) ЖЁСТКО: один LangChain-session_id = task.context_id
        session_id = task.context_id or getattr(context, "context_id", None) or task.id

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        # 3) Стримим ответ агента
        async for item in self.agent.stream(query, session_id):
            is_task_complete = item["is_task_complete"]
            require_user_input = item["require_user_input"]
            is_error = item["is_error"]
            is_event = item["is_event"]
            content = item["content"]

            if is_error:
                await updater.update_status(
                    TaskState.failed,
                    new_agent_text_message(content, task.context_id, task.id),
                    final=True,
                )
                break

            if is_event:
                # промежуточные события (типы "Использую инструмент: ...")
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(content, task.context_id, task.id),
                )
                continue

            # Стримим промежуточный текст (LLM ответ по кускам)
            if not is_task_complete and not require_user_input:
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(content, task.context_id, task.id),
                )
                continue

            # Модели нужен ответ пользователя
            if not is_task_complete and require_user_input:
                await updater.update_status(
                    TaskState.input_required,
                    new_agent_text_message(content, task.context_id, task.id),
                    final=True,
                )
                break

            # Задача полностью завершена, ввод пользователя не нужен
            if is_task_complete and not require_user_input:
                await updater.update_status(
                    TaskState.completed,
                    new_agent_text_message(content, task.context_id, task.id),
                    final=True,
                )
                break

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
