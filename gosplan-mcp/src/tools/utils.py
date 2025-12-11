"""Утилиты для работы с ГосПлан API и форматирования ответов."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, List, Optional

import httpx
from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent

from config import get_settings
from .models import (
    AttachmentInfo,
    ClassifierCode,
    CustomerInfo,
    LawLiteral,
    LocationInfo,
    PlatformInfo,
    PreferenceInfo,
    PurchaseFeatures,
    PurchaseListItem,
    PurchaseObjectItem,
    RequirementInfo,
    SearchPurchasesParams,
    TimelineInfo,
    PriceInfo,
)


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


def create_http_client() -> httpx.AsyncClient:
    """Создает настроенный HTTP клиент для запросов к ГосПлан."""

    settings = get_settings()
    return httpx.AsyncClient(
        base_url=str(settings.gosplan_base_url),
        timeout=settings.gosplan_timeout_seconds,
        headers={"User-Agent": "gosplan-mcp/2.0"},
    )


def parse_datetime(value: Any) -> Optional[datetime]:
    """Безопасный парсинг ISO-строк даты/времени."""

    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


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


def format_purchase_summary(purchase: PurchaseListItem) -> str:
    """Краткое текстовое представление закупки."""

    stage_map = {
        1: "подача заявок",
        2: "рассмотрение",
        3: "определение победителя",
        4: "заключение договора",
    }

    close_at_str = (
        purchase.submission_close_at.isoformat()
        if purchase.submission_close_at
        else "нет данных"
    )
    max_price_str = (
        f"{purchase.max_price:,.2f}".replace(",", " ") if purchase.max_price else "нет данных"
    )

    return (
        f"Номер: {purchase.purchase_number}\n"
        f"Закон: {purchase.law}\n"
        f"Описание: {purchase.object_info or 'нет данных'}\n"
        f"Цена: {max_price_str} {purchase.currency_code}\n"
        f"Окончание приема: {close_at_str}\n"
        f"Стадия: {stage_map.get(purchase.stage, 'неизвестно')}\n"
        f"Регион: {purchase.region or 'нет данных'}\n"
        f"ОКПД2: {', '.join(purchase.okpd2) if purchase.okpd2 else 'нет данных'}"
    )


def format_purchase_list(purchases: List[PurchaseListItem]) -> str:
    """Формирует текстовый список закупок для ответа LLM."""

    header = f"Показано: {len(purchases)}\n\n" if purchases else "Результаты не найдены"
    formatted_items = []

    for idx, purchase in enumerate(purchases, start=1):
        formatted_items.append(f"{idx}.\n{format_purchase_summary(purchase)}")

    return header + ("\n\n".join(formatted_items) if formatted_items else "")


def format_purchase_details(purchase: PurchaseFeatures) -> str:
    """Подробное описание закупки с приложениями и местами поставки."""

    lines = [
        f"Номер закупки: {purchase.purchase_number} ({purchase.law})",
        f"Название: {purchase.title or purchase.short_description or 'нет данных'}",
        f"Заказчик: {purchase.customer.full_name or purchase.customer.short_name or 'нет данных'}",
        f"НМЦК: {purchase.price.initial_price:,.2f} {purchase.price.currency_code}".replace(",", " "),
    ]

    if purchase.timeline.applications_end:
        lines.append(
            f"Окончание подачи заявок: {purchase.timeline.applications_end.isoformat()}"
        )
    if purchase.timeline.published_at:
        lines.append(f"Опубликовано: {purchase.timeline.published_at.isoformat()}")

    if purchase.classifiers:
        classifier_text = ", ".join(f"{c.code} ({c.system})" for c in purchase.classifiers)
        lines.append(f"Классификаторы: {classifier_text}")

    if purchase.delivery_locations:
        lines.append("Места поставки:")
        for loc in purchase.delivery_locations:
            parts = [loc.region_name or loc.region_code, loc.locality_name, loc.raw_address]
            address = ", ".join(filter(None, parts)) or "нет данных"
            lines.append(f"  - {address}")

    if purchase.attachments:
        lines.append(f"Документы ({len(purchase.attachments)}):")
        for attachment in purchase.attachments:
            lines.append(
                f"  - {attachment.file_name} ({attachment.kind_name or 'документ'}) — {attachment.url}"
            )

    if purchase.objects:
        lines.append("Объекты закупки:")
        for obj in purchase.objects:
            codes = ", ".join(c.code for c in obj.classifiers) if obj.classifiers else ""
            lines.append(
                f"  - {obj.name or 'позиция'}" + (f" [{codes}]" if codes else "")
            )

    if purchase.plan_numbers:
        lines.append(f"Планы: {', '.join(purchase.plan_numbers)}")

    return "\n".join(lines)


def extract_customer_info(doc: dict[str, Any]) -> CustomerInfo:
    """Извлекает информацию о заказчике из документа источника."""

    main_info = (
        doc.get("customer", {}).get("mainInfo")
        or doc.get("purchaseResponsibleInfo", {}).get("responsibleOrgInfo", {})
    )
    return CustomerInfo(
        inn=main_info.get("inn") if isinstance(main_info, dict) else None,
        kpp=main_info.get("kpp") if isinstance(main_info, dict) else None,
        ogrn=main_info.get("ogrn") if isinstance(main_info, dict) else None,
        full_name=main_info.get("fullName") if isinstance(main_info, dict) else None,
        short_name=main_info.get("shortName") if isinstance(main_info, dict) else None,
        customer_reg_num=main_info.get("iko") if isinstance(main_info, dict) else None,
        region_name=main_info.get("regionName") if isinstance(main_info, dict) else None,
        legal_address=main_info.get("legalAddress") if isinstance(main_info, dict) else None,
        postal_address=main_info.get("postalAddress") if isinstance(main_info, dict) else None,
        email=main_info.get("email") if isinstance(main_info, dict) else None,
        phone=main_info.get("phone") if isinstance(main_info, dict) else None,
    )


def extract_platform_info(doc: dict[str, Any], law: LawLiteral) -> PlatformInfo:
    placing_way = doc.get("commonInfo", {}).get("placingWay") if isinstance(doc, dict) else None
    etp = doc.get("commonInfo", {}).get("ETP") if isinstance(doc, dict) else None

    return PlatformInfo(
        law=law,
        placing_way_code=placing_way.get("code") if isinstance(placing_way, dict) else None,
        placing_way_name=placing_way.get("name") if isinstance(placing_way, dict) else None,
        etp_code=etp.get("code") if isinstance(etp, dict) else None,
        etp_name=etp.get("name") if isinstance(etp, dict) else None,
        etp_url=etp.get("url") if isinstance(etp, dict) else None,
        is_electronic=bool(etp) if etp else None,
    )


def extract_delivery_locations(raw: dict[str, Any]) -> list[LocationInfo]:
    locations: list[LocationInfo] = []
    for place in raw.get("delivery_places", []) or []:
        locations.append(LocationInfo(raw_address=str(place)))

    for kladr in raw.get("delivery_places_kladr", []) or []:
        locations.append(LocationInfo(kladr_or_okato=str(kladr)))

    return locations


def extract_classifiers(okpd2_list: Iterable[str]) -> list[ClassifierCode]:
    return [ClassifierCode(system="OKPD2", code=code) for code in okpd2_list]


def extract_attachments(doc: dict[str, Any]) -> list[AttachmentInfo]:
    attachments_block = doc.get("attachmentsInfo", {}).get("attachmentInfo", []) if isinstance(doc, dict) else []
    attachments: list[AttachmentInfo] = []

    for attachment in attachments_block or []:
        if not isinstance(attachment, dict):
            continue
        size_str = attachment.get("fileSize")
        attachments.append(
            AttachmentInfo(
                uid=attachment.get("publishedContentId"),
                kind_code=(attachment.get("docKindInfo") or {}).get("code"),
                kind_name=(attachment.get("docKindInfo") or {}).get("name"),
                file_name=attachment.get("fileName", "Документ"),
                description=attachment.get("docDescription"),
                url=attachment.get("url"),
                size_bytes=int(size_str) if size_str and str(size_str).isdigit() else None,
                doc_date=parse_datetime(attachment.get("docDate")),
            )
        )

    return attachments


def extract_objects(doc: dict[str, Any]) -> list[PurchaseObjectItem]:
    purchase_objects = (
        doc.get("notificationInfo", {})
        .get("purchaseObjectsInfo", {})
        .get("purchaseObject")
    )
    objects: list[PurchaseObjectItem] = []

    if isinstance(purchase_objects, list):
        iterable = purchase_objects
    elif purchase_objects:
        iterable = [purchase_objects]
    else:
        iterable = []

    for obj in iterable:
        if not isinstance(obj, dict):
            continue
        classifiers = []
        if isinstance(obj.get("KTRU"), dict):
            ktru = obj["KTRU"]
            classifiers.append(
                ClassifierCode(system="KTRU", code=ktru.get("code", ""), name=ktru.get("name"))
            )
            okpd = ktru.get("OKPD2", {}) if isinstance(ktru, dict) else {}
            if isinstance(okpd, dict) and okpd.get("OKPDCode"):
                classifiers.append(
                    ClassifierCode(
                        system="OKPD2", code=okpd.get("OKPDCode", ""), name=okpd.get("OKPDName")
                    )
                )

        objects.append(
            PurchaseObjectItem(
                name=obj.get("name"),
                classifiers=classifiers,
                ktru_code=(obj.get("KTRU") or {}).get("code") if isinstance(obj.get("KTRU"), dict) else None,
                quantity=float(obj.get("quantity", {}).get("value"))
                if isinstance(obj.get("quantity"), dict) and obj.get("quantity", {}).get("value")
                else None,
                quantity_unit_code=(obj.get("OKEI") or {}).get("code") if isinstance(obj.get("OKEI"), dict) else None,
                quantity_unit_name=(obj.get("OKEI") or {}).get("name") if isinstance(obj.get("OKEI"), dict) else None,
                price_per_unit=float(obj.get("price")) if obj.get("price") else None,
                total_sum=float(obj.get("sum")) if obj.get("sum") else None,
                object_type=obj.get("type"),
            )
        )

    return objects


def build_purchase_features(raw: dict[str, Any], law: LawLiteral) -> PurchaseFeatures:
    """Собирает нормализованную модель PurchaseFeatures из ответа API."""

    doc = (raw.get("docs") or [{}])[0].get("source", {}) if raw.get("docs") else {}

    classifiers = extract_classifiers(raw.get("okpd2") or [])
    objects = extract_objects(doc)
    attachments = extract_attachments(doc)
    locations = extract_delivery_locations(raw)

    price = PriceInfo(
        currency_code=raw.get("currency_code", "RUB"),
        initial_price=float(raw.get("max_price") or 0.0),
        contract_guarantee_amount=raw.get("contract_guarantee_amount"),
        contract_guarantee_part=raw.get("contract_guarantee_part"),
    )

    timeline = TimelineInfo(
        published_at=parse_datetime(raw.get("published_at")),
        updated_at=parse_datetime(raw.get("updated_at")),
        applications_end=parse_datetime(raw.get("submission_close_at")),
        collecting_finished_at=parse_datetime(raw.get("collecting_finished_at")),
    )

    requirements_block = (
        doc.get("notificationInfo", {})
        .get("requirementsInfo", {})
        .get("requirement")
    )
    if isinstance(requirements_block, dict):
        requirements_iter = [requirements_block]
    elif isinstance(requirements_block, list):
        requirements_iter = requirements_block
    else:
        requirements_iter = []

    preferences_block = (
        doc.get("notificationInfo", {}).get("preferensesInfo", {}).get("preferense")
    )
    if isinstance(preferences_block, dict):
        preferences_iter = [preferences_block]
    elif isinstance(preferences_block, list):
        preferences_iter = preferences_block
    else:
        preferences_iter = []

    return PurchaseFeatures(
        source_system="GOSPLAN",
        law=law,
        purchase_number=raw.get("purchase_number", ""),
        lot_number=None,
        lot_internal_id=None,
        ikz=(raw.get("ikzs") or [None])[0] if raw.get("ikzs") else None,
        plan_numbers=raw.get("plan_numbers") or [],
        plan_position_numbers=raw.get("position_numbers") or [],
        title=raw.get("object_info"),
        short_description=raw.get("object_info"),
        extended_description=None,
        stage=raw.get("stage"),
        status=raw.get("purchase_type"),
        is_cancelled=None,
        customer=extract_customer_info(doc),
        platform=extract_platform_info(doc, law),
        delivery_locations=locations,
        timeline=timeline,
        price=price,
        classifiers=classifiers,
        objects=objects,
        requirements=[
            RequirementInfo(name=req.get("name", "Требование"), code=req.get("code"))
            for req in requirements_iter
            if isinstance(req, dict)
        ],
        preferences=[
            PreferenceInfo(name=pref.get("name", "Преимущество"), code=pref.get("code"))
            for pref in preferences_iter
            if isinstance(pref, dict)
        ],
        sme_only=None,
        sme_preference=None,
        card_urls=[
            url
            for url in [raw.get("card_url"), (doc.get("commonInfo", {}) or {}).get("href")]
            if url
        ],
        attachments=attachments,
        extra={"raw": raw},
    )


def filter_and_slice_results(
    purchases: List[PurchaseListItem],
    params: SearchPurchasesParams,
) -> List[PurchaseListItem]:
    """Применяет клиентские фильтры и ограничение по количеству."""

    filtered: list[PurchaseListItem] = []
    for item in purchases:
        if params.region_codes and item.region is not None and item.region not in params.region_codes:
            continue
        if params.applications_end_before and item.submission_close_at:
            if item.submission_close_at > params.applications_end_before:
                continue
        filtered.append(item)
        if len(filtered) >= params.limit:
            break

    return filtered
