import os
import json
from uuid import uuid4
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest

# Путь к файлу с профилями (будем сохранять сюда)
PROFILES_PATH = Path("data/profiles.json")


class MessagePayload(BaseModel):
    message: str
    session_id: str


def load_profiles_from_disk() -> List[Dict[str, Any]]:
    if PROFILES_PATH.exists():
        try:
            raw = PROFILES_PATH.read_text(encoding="utf-8")
            data = json.loads(raw)
            return data.get("profiles", [])
        except Exception:
            return []
    return []


def save_profiles_to_disk(profiles: List[Dict[str, Any]]) -> None:
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {"profiles": profiles}
    PROFILES_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def extract_profile_from_text(assistant_text: str) -> Optional[Dict[str, Any]]:
    """
    Пытаемся вытащить JSON с полями company_id и profile.name
    из текста ответа агента. Типичный формат:

    <think>...</think>

    {
      "status": "...",
      "company_id": "...",
      "profile": {
        "name": "...",
        ...
      }
    }
    """
    if not assistant_text:
        return None

    text = assistant_text.strip()
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        return None

    candidate = text[first : last + 1]

    try:
        obj = json.loads(candidate)
    except Exception:
        return None

    company_id = obj.get("company_id")
    profile = obj.get("profile") or {}
    company_name = profile.get("name")

    if not company_id or not company_name:
        return None

    return {
        "company_id": company_id,
        "company_name": company_name,
        "profile": profile,
        "raw": obj,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


async def lifespan(app: FastAPI):
    """
    Startup / shutdown: создаём httpx-клиент, резолвер и A2AClient,
    поднимаем кеш профилей.
    """
    # Базовый URL до твоего A2A-агента
    # Можно переопределить через переменную окружения A2A_BASE_URL
    base_url = os.environ.get("A2A_BASE_URL", "http://localhost:28003")

    httpx_client = httpx.AsyncClient(timeout=None)
    resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
    agent_card = await resolver.get_agent_card()
    a2a_client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

    app.state.httpx_client = httpx_client
    app.state.a2a_client = a2a_client

    profiles = load_profiles_from_disk()
    app.state.profiles = profiles

    try:
        save_profiles_to_disk(profiles)
    except Exception:
        pass

    yield

    await httpx_client.aclose()


app = FastAPI(lifespan=lifespan)

# Отдаём статику (index.html)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    index_path = Path("static/index.html")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.get("/api/profiles")
async def get_profiles() -> JSONResponse:
    profiles = app.state.profiles
    # Возвращаем облегчённую версию
    short = [
        {
            "company_id": p.get("company_id"),
            "company_name": p.get("company_name"),
            "created_at": p.get("created_at"),
        }
        for p in profiles
    ]
    return JSONResponse({"profiles": short})


@app.post("/api/message")
async def send_message(payload: MessagePayload) -> JSONResponse:
    client: A2AClient = app.state.a2a_client

    req = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message={
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": payload.message,
                    }
                ],
                "messageId": uuid4().hex,
            },
            metadata={"session_id": payload.session_id},
        ),
    )

    try:
        resp = await client.send_message(req)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Ошибка при обращении к A2A агенту", "detail": str(e)},
        )

    data = resp.model_dump(mode="json", exclude_none=True)
    result = data.get("result") or {}
    history = result.get("history") or []

    assistant_text: Optional[str] = None

    if history:
        assistant_msg: Optional[Dict[str, Any]] = None

        for msg in reversed(history):
            if msg.get("role") == "user":
                continue
            assistant_msg = msg
            break

        if assistant_msg is None and len(history) >= 2:
            assistant_msg = history[-2]

        if assistant_msg:
            parts = assistant_msg.get("parts", [])
            texts = [p.get("text", "") for p in parts if p.get("kind") == "text"]
            assistant_text = "\n".join(texts).strip() if texts else None

    saved_profile_short: Optional[Dict[str, Any]] = None

    if assistant_text:
        profile_obj = extract_profile_from_text(assistant_text)
        if profile_obj:
            profiles: List[Dict[str, Any]] = app.state.profiles

            for i, existing in enumerate(profiles):
                if existing.get("company_id") == profile_obj["company_id"]:
                    profiles[i] = profile_obj
                    break
            else:
                profiles.append(profile_obj)

            app.state.profiles = profiles
            save_profiles_to_disk(profiles)

            saved_profile_short = {
                "company_id": profile_obj["company_id"],
                "company_name": profile_obj["company_name"],
                "created_at": profile_obj["created_at"],
            }

    return JSONResponse(
        {
            "assistant_text": assistant_text,
            "raw": data,
            "saved_profile": saved_profile_short,
        }
    )
