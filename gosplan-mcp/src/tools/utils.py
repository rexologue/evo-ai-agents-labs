"""Утилиты для форматирования ответов и проверки окружения."""

import json
import os
from dataclasses import dataclass
from typing import Any

from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent


@dataclass
class ToolResult:
    """Стандартная обертка для результатов MCP инструмента."""

    content: list[TextContent]
    structured_content: dict[str, Any] | list[dict[str, Any]]
    meta: dict[str, Any]


def check_required_env_vars(required_vars: list[str]) -> None:
    """Проверяет, что обязательные переменные окружения заполнены."""

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise McpError(
            ErrorData(
                code=-32602,
                message=(
                    "Не заданы обязательные переменные окружения: "
                    + ", ".join(sorted(missing))
                ),
            )
        )


def format_api_error(api_error: str, code: int) -> str:
    """Возвращает удобочитаемое описание ошибки API."""

    try:
        parsed = json.loads(api_error) if api_error else {}
    except json.JSONDecodeError:
        parsed = api_error

    if code == 404:
        return "Запись не найдена"

    if code == 422:
        details: list[str] = []

        if isinstance(parsed, dict) and "detail" in parsed:
            detail = parsed["detail"]
            if isinstance(detail, list):
                for item in detail:
                    if isinstance(item, dict):
                        location = ".".join(str(part) for part in item.get("loc", []))
                        message = item.get("msg", "Неизвестная ошибка")
                        if location:
                            details.append(f"{location}: {message}")
                        else:
                            details.append(message)
                    else:
                        details.append(str(item))
            else:
                details.append(str(detail))
        elif parsed:
            details.append(str(parsed))
        else:
            details.append("Ошибки валидации")

        return "Ошибки валидации:\n  - " + "\n  - ".join(details)

    if isinstance(parsed, dict) and "detail" in parsed:
        return str(parsed["detail"])

    if isinstance(parsed, dict):
        return json.dumps(parsed, ensure_ascii=False)

    return str(api_error) if api_error else "Неизвестная ошибка"


def format_purchase_summary(purchase: dict[str, Any]) -> str:
    """Краткое текстовое представление закупки."""

    stage_map = {
        1: "подача заявок",
        2: "рассмотрение",
        3: "определение победителя",
        4: "заключение договора",
    }

    okpd2_codes = ", ".join(purchase.get("okpd2") or [])
    close_at = purchase.get("submission_close_at")
    close_at_str = str(close_at) if close_at else "нет данных"

    max_price = purchase.get("max_price")
    max_price_str = f"{max_price:,.2f}" if max_price else "нет данных"

    return (
        f"Номер закупки: {purchase.get('purchase_number', '—')}\n"
        f"Заказчик: {purchase.get('customer', 'нет данных')}\n"
        f"Описание: {purchase.get('object_info', 'нет данных')}\n"
        f"Начальная цена: {max_price_str} {purchase.get('currency_code', '')}\n"
        f"Окончание приема заявок: {close_at_str}\n"
        f"Стадия: {stage_map.get(purchase.get('stage'), 'неизвестно')}\n"
        f"Регион: {purchase.get('region', 'нет данных')}\n"
        f"ОКПД2: {okpd2_codes or 'нет данных'}"
    )
    """Формирует список закупок для текстового ответа."""

    header = f"Всего закупок: {total}\nПоказано: {len(purchases)}\n\n"

    """Подробное описание закупки для вывода в LLM."""
        text += "\n\nМеста поставки:\n"
    text += f"\n\nДокументы закупки ({len(docs)}):\n"
        text += f"  - {doc['doc_type']} (опубликован: {doc['published_at']})\n"

            f"\n\nСвязанные планы закупок: {', '.join(purchase['plan_numbers'])}\n"
    """
    $>@<0B8@>20=85 45B0;L=>9 8=D>@<0F88 > 70:C?:5 A 4>:C<5=B0<8.

    Args:
        purchase: !;>20@L A 40==K<8 70:C?:8

    Returns:
        BD>@<0B8@>20==K9 B5:AB
    """
    text = format_purchase_summary(purchase)

    # >102;O5< <5AB0 ?>AB02:8
    if purchase.get("delivery_places"):
        text += "\n\n5AB0 ?>AB02:8:\n"
        for place in purchase["delivery_places"]:
            text += f"  - {place}\n"

    # >102;O5< 4>:C<5=BK
    docs = purchase.get("docs", [])
    text += f"\n\n>:C<5=BK 70:C?:8 ({len(docs)}):\n"
    for doc in docs:
        text += f"  - {doc['doc_type']} (>?C1;8:>20=>: {doc['published_at']})\n"

    # >102;O5< A2O70==K5 ?;0=K
    if purchase.get("plan_numbers"):
        text += (
            f"\n\n!2O70==K5 ?;0=K 70:C?>:: {', '.join(purchase['plan_numbers'])}\n"
        )

    return text
