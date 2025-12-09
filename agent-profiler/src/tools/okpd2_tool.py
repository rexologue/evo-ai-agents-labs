from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from langchain_core.tools import BaseTool, Tool

from models import Okpd2Item

DATA_PATH = Path(__file__).parent.parent / "data" / "okpd2.csv"

def load_okpd2_index() -> List[Okpd2Item]:
    items: List[Okpd2Item] = []
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Не найден okpd2.csv по пути {DATA_PATH}")
    with DATA_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("code"):
                continue
            items.append(Okpd2Item(code=row["code"].strip(), title=row.get("category", "").strip()))
    return items


OKPD2_INDEX = load_okpd2_index()


def build_okpd2_tool() -> BaseTool:
    """Строит LangChain Tool, который отдаёт подсказку по кодам ОКПД2."""

    def _okpd2_hint(_: str) -> str:
        """
        На вход может принимать любой текст (игнорируется).
        Возвращает JSON-объект с подсказкой по кодам ОКПД2.

        Формат:
        {
          "hint": "строка с инструкцией для модели",
          "items": [
            {"code": "...", "title": "..."},
            ...
          ]
        }

        Модель читает этот список и уже сама выбирает
        подходящие коды в своём ответе.
        """

        items = [
            {
                "code": item.code,
                "title": item.title,
            }
            for item in OKPD2_INDEX
        ]

        payload = {
            "hint": (
                "Это справочник кодов ОКПД2. Используй его, чтобы самостоятельно "
                "подобрать несколько (обычно 1–5) наиболее подходящих кодов для "
                "описания компании. В своём ответе укажи только выбранные коды и их "
                "названия, без переписывания всего списка."
            ),
            "items": items,
        }

        return json.dumps(payload, ensure_ascii=False)

    return Tool(
        name="okpd2_codes_hint",
        description=(
            "Возвращает справочник ОКПД2 в виде JSON: {hint, items:[{code, title}]}. "
            "Используй этот инструмент, когда тебе нужен список кодов ОКПД2, чтобы, "
            "проанализировав его, самостоятельно выбрать подходящие коды для okpd2_codes."
        ),
        func=_okpd2_hint,
    )