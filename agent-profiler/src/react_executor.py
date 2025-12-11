from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

_ACTION_RE = re.compile(r"^\s*Action\s*:\s*(?P<name>[^\n\r]+)\s*$", re.I | re.M)
_ACTION_INPUT_RE = re.compile(
    r"^\s*Action\s*Input\s*:\s*(?P<body>.+?)\s*$", re.I | re.M | re.S
)
_FINAL_RE = re.compile(r"^\s*Final\s*:\s*(?P<body>.+?)\s*$", re.I | re.M | re.S)

_CODE_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$", re.S)

_REACT_INSTRUCTIONS = """\
Ты можешь пользоваться инструментами.

Чтобы вызвать инструмент, выведи СТРОГО (без лишнего текста вокруг):

Action: <tool_name>
Action Input: <валидный JSON-объект>

После получения результата инструмента продолжай работу: либо вызывай следующий инструмент,
либо отвечай пользователю обычным текстом.

ЖЁСТКИЕ ПРАВИЛА:
- НИКОГДА не выдумывай результаты инструментов.
- НИКОГДА не выдумывай company_id или любые идентификаторы.
- Не говори «инструмент недоступен/не поддерживается», если у тебя нет Observation с ошибкой реального вызова.
- Если нужен company_id — ОБЯЗАТЕЛЬНО вызови create_company_profile и возьми id из ответа тулзы.
"""


def _strip_code_fences(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("```"):
        s = _CODE_FENCE_RE.sub("", s).strip()
    return s


def _parse_json_obj(s: str) -> Optional[dict]:
    s = _strip_code_fences(s)
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _first_group(rx: re.Pattern[str], text: str, name: str) -> Optional[str]:
    m = rx.search(text or "")
    if not m:
        return None
    val = (m.group(name) or "").strip()
    return val or None


async def _ainvoke_tool(tool: BaseTool, args: dict) -> Any:
    # Предпочитаем async, потому что MCP инструменты почти всегда async.
    if hasattr(tool, "ainvoke"):
        try:
            return await tool.ainvoke(args)
        except TypeError:
            return await tool.ainvoke(**args)

    # Fallback на sync invoke
    if hasattr(tool, "invoke"):
        try:
            return tool.invoke(args)
        except TypeError:
            return tool.invoke(**args)

    raise RuntimeError(f"Tool {getattr(tool, 'name', '<unknown>')} has no invoke/ainvoke")


def _invoke_tool_sync(tool: BaseTool, args: dict) -> Any:
    # Мы почти всегда вызываем это из отдельного worker thread (через run_in_executor),
    # поэтому можем безопасно крутить отдельный event loop.
    return asyncio.run(_ainvoke_tool(tool, args))


@dataclass
class ToolAction:
    tool: str
    tool_input: dict


class ReActExecutor:
    """Минимальный ReAct-цикл, не зависящий от native tool-calling."""

    def __init__(
        self,
        llm: Any,
        tools: Iterable[BaseTool],
        system_prompt: str,
        max_iterations: int = 20,
        max_observation_chars: int = 8000,
    ) -> None:
        self.llm = llm
        self.tools: List[BaseTool] = list(tools or [])
        self.tool_map: Dict[str, BaseTool] = {getattr(t, "name", ""): t for t in self.tools}
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.max_observation_chars = max_observation_chars

        self._tools_text = self._render_tools_text()

    def _render_tools_text(self) -> str:
        lines: List[str] = []
        for t in self.tools:
            name = getattr(t, "name", "<unnamed>")
            desc = (getattr(t, "description", "") or "").strip()
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines) if lines else "<no tools>"

    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        user_input = (inputs or {}).get("input", "") or ""
        chat_history: List[BaseMessage] = (inputs or {}).get("chat_history") or []

        intermediate_steps: List[Tuple[ToolAction, Any]] = []
        scratchpad = ""

        for _ in range(self.max_iterations):
            messages: List[BaseMessage] = [
                SystemMessage(
                    content=(
                        self.system_prompt.strip()
                        + "\n\n---\nДОСТУПНЫЕ ИНСТРУМЕНТЫ:\n"
                        + self._tools_text
                        + "\n---\n"
                        + _REACT_INSTRUCTIONS
                        + "\n\n"
                        + "Твой scratchpad будет передан как есть, опирайся на него."
                    )
                )
            ]
            if chat_history:
                messages.extend(chat_history)
            if scratchpad.strip():
                messages.append(AIMessage(content=f"[scratchpad]\n{scratchpad}\n[/scratchpad]"))
            messages.append(HumanMessage(content=user_input))

            llm_resp = self.llm.invoke(messages)
            raw = str(getattr(llm_resp, "content", llm_resp) or "").strip()
            if not raw:
                return {"output": "", "intermediate_steps": intermediate_steps}

            action_name = _first_group(_ACTION_RE, raw, "name")
            if action_name:
                action_name = action_name.strip()
                tool = self.tool_map.get(action_name)
                if tool is None:
                    scratchpad += (
                        f"\nObservation: ERROR unknown tool '{action_name}'. "
                        f"Use one of: {', '.join([k for k in self.tool_map.keys() if k])}\n"
                    )
                    continue

                action_input_text = _first_group(_ACTION_INPUT_RE, raw, "body") or ""
                args = _parse_json_obj(action_input_text)
                if args is None:
                    scratchpad += "\nObservation: ERROR invalid JSON in Action Input. Provide a JSON object.\n"
                    continue

                logger.info("ReAct tool call: %s args=%s", action_name, args)

                try:
                    obs = _invoke_tool_sync(tool, args)
                except Exception as exc:
                    intermediate_steps.append((ToolAction(tool=action_name, tool_input=args), {"error": str(exc)}))
                    scratchpad += f"\nObservation: ERROR calling tool '{action_name}': {exc}\n"
                    continue

                intermediate_steps.append((ToolAction(tool=action_name, tool_input=args), obs))

                try:
                    obs_txt = json.dumps(obs, ensure_ascii=False)
                except Exception:
                    obs_txt = str(obs)

                if len(obs_txt) > self.max_observation_chars:
                    obs_txt = obs_txt[: self.max_observation_chars] + "...(truncated)"

                scratchpad += (
                    f"\nAction: {action_name}\n"
                    f"Action Input: {json.dumps(args, ensure_ascii=False)}\n"
                    f"Observation: {obs_txt}\n"
                )
                continue

            final_body = _first_group(_FINAL_RE, raw, "body")
            final_text = (final_body if final_body is not None else raw).strip()
            return {"output": final_text, "intermediate_steps": intermediate_steps}

        return {
            "output": "Ошибка: превышен лимит итераций агента. Попробуйте уточнить ввод.",
            "intermediate_steps": intermediate_steps,
        }

    async def astream(self, inputs: Dict[str, Any]):
        # Стрим “одним куском”, но совместимый с текущей A2A обёрткой.
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: self.invoke(inputs))
        yield {"output": result.get("output", ""), "intermediate_steps": result.get("intermediate_steps", [])}
