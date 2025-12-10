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
    """Проверяет, что обязательные переменные окружения заполнены."""


    """Возвращает удобочитаемое описание ошибки API."""
        return "Запись не найдена"
    if code == 422:
                return "Ошибки валидации:\n  - " + "\n  - ".join(messages)

    """Краткое текстовое представление закупки."""
        1: "подача заявок",
        2: "рассмотрение",
        3: "определение победителя",
        4: "заключение договора",
    close_at_str = close_at if close_at else "нет данных"
    max_price_str = f"{max_price:,.2f}" if max_price else "нет данных"
Номер закупки: {purchase['purchase_number']}
Заказчик: {purchase['customer']}
Описание: {purchase['object_info']}
Начальная цена: {max_price_str} {purchase['currency_code']}
Окончание приема заявок: {close_at_str}
Стадия: {stage_map.get(purchase['stage'], 'неизвестно')}
Регион: {purchase['region']}
ОКПД2: {okpd2_codes or 'нет данных'}
    """Формирует список закупок для текстового ответа."""
    header = f"Всего закупок: {total}\nПоказано: {len(purchases)}\n\n"
    """Подробное описание закупки для вывода в LLM."""
        text += "\n\nМеста поставки:\n"
    text += f"\n\nДокументы закупки ({len(docs)}):\n"
        text += f"  - {doc['doc_type']} (опубликован: {doc['published_at']})\n"
            f"\n\nСвязанные планы закупок: {', '.join(purchase['plan_numbers'])}\n"
        4: "0:C?:0 >B<5=5=0",
    }

    okpd2_codes = ", ".join(purchase.get("okpd2") or [])
    close_at = purchase.get("submission_close_at")
    close_at_str = close_at if close_at else "=5 C:070=>"

    max_price = purchase.get("max_price", 0)
    max_price_str = f"{max_price:,.2f}" if max_price else "=5 C:070=>"

    return f"""---
><5@ 70:C?:8: {purchase['purchase_number']}
0:07G8: (): {purchase['customer']}
@54<5B: {purchase['object_info']}
0:A8<0;L=0O F5=0: {max_price_str} {purchase['currency_code']}
:>=G0=85 ?>40G8 70O2>:: {close_at_str}
-B0?: {stage_map.get(purchase['stage'], '=58725AB=>')}
 538>=: {purchase['region']}
2: {okpd2_codes or '=5 C:070=>'}
---"""


def format_purchase_list(purchases: list[dict[str, Any]], total: int) -> str:
    """
    $>@<0B8@>20=85 A?8A:0 70:C?>:.

    Args:
        purchases: !?8A>: 70:C?>:
        total: 1I55 :>;8G5AB2> =0945==KE 70:C?>:

    Returns:
        BD>@<0B8@>20==K9 B5:AB
    """
    header = f"0945=> 70:C?>:: {total}\n>:070=>: {len(purchases)}\n\n"
    summaries = [format_purchase_summary(p) for p in purchases]
    return header + "\n\n".join(summaries)


def format_purchase_details(purchase: dict[str, Any]) -> str:
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
