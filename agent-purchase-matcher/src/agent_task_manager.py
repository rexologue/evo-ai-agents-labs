"""Интеграция PurchaseMatcher с A2A задачами."""
from __future__ import annotations

import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Task, TaskState, UnsupportedOperationError
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from .a2a_wrapper import PurchaseMatcherA2AWrapper

logger = logging.getLogger(__name__)


class PurchaseMatcherExecutor(AgentExecutor):
    def __init__(self, wrapper: PurchaseMatcherA2AWrapper) -> None:
        self.wrapper = wrapper

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = context.get_user_input()
        task = context.current_task

        session_id = None
        metadata = getattr(context, "metadata", None) or {}
        if isinstance(metadata, dict):
            session_id = metadata.get("session_id")
        session_id = session_id or getattr(context, "context_id", None) or "default"

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        async for item in self.wrapper.stream(query, session_id):
            if item.get("is_error"):
                await updater.update_status(
                    TaskState.failed,
                    new_agent_text_message(item.get("content"), task.context_id, task.id),
                )
                break

            if item.get("require_user_input"):
                await updater.update_status(
                    TaskState.input_required,
                    new_agent_text_message(item.get("content"), task.context_id, task.id),
                )
                break

            state = TaskState.completed if item.get("is_task_complete") else TaskState.working
            await updater.update_status(
                state,
                new_agent_text_message(item.get("content"), task.context_id, task.id),
            )
            if item.get("is_task_complete"):
                break

    async def cancel(self, request: RequestContext, event_queue: EventQueue) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
