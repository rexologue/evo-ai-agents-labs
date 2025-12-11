"""Утилиты для работы с ГосПлан API и форматирования ответов."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, List, Optional

import httpx
from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent

from config import get_settings
from models import (
    AttachmentInfo,
    ClassifierCode,
    CustomerInfo,
    LawLiteral,
    LocationInfo,
    PlatformInfo,
    PreferenceInfo,
    PriceInfo,
    PurchaseFeatures,
    PurchaseListItem,
    PurchaseObjectItem,
    RequirementInfo,
    SearchPurchasesParams,
    TimelineInfo,
)

_DATE_WITH_TZ_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[+-]\d{2}:\d{2}$")


@dataclass
class ToolResult:
    """Стандартная обертка для результатов MCP инструмента."""

    content: list[TextContent]
    structured_content: dict[str, Any] | list[dict[str, Any]]
    meta: dict[str, Any]


def _pick(d: Any, *keys: str) -> Any:
    """Берёт первое непустое значение по одному из ключей (с учётом разных регистров/вариантов)."""
    if not isinstance(d, dict):
        return None
    for k in keys:
        v = d.get(k)
        if v not in (None, "", [], {}):
            return v
    return None


def _safe_get(obj: Any, *path: str) -> Any:
    """Безопасный доступ по цепочке ключей."""
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _as_list(v: Any) -> list:
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        return [v]
    return []


def _uniq_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if not v:
            continue
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def _walk_collect_values_for_key(obj: Any, key: str) -> list[Any]:
    """Рекурсивно собирает значения по ключу key из dict/list."""
    found: list[Any] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                found.append(v)
            found.extend(_walk_collect_values_for_key(v, key))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_walk_collect_values_for_key(item, key))
    return found


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

    s = str(value).strip()
    if not s:
        return None

    # "2025-12-11+03:00" -> "2025-12-11T00:00:00+03:00"
    if _DATE_WITH_TZ_RE.match(s):
        s = s[:10] + "T00:00:00" + s[10:]

    # Z -> +00:00
    s = s.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(s)
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


def classify_urls(
    card_urls: Iterable[Any] | None,
    etp_url: Any | None = None,
) -> dict[str, Any]:
    """
    Классифицирует ссылки для LLM/JSONL, чтобы НЕ приходилось «догадываться».
    Предпочтение для EIS: страницы notice/common-info, затем любые zakupki.gov.ru.
    """
    urls = _uniq_preserve_order([str(u) for u in (card_urls or []) if u])

    etp_url_str = str(etp_url) if etp_url else None

    eis: str | None = None
    gosplan: str | None = None

    # EIS — сначала самые “карточные” ссылки
    eis_candidates = [u for u in urls if "zakupki.gov.ru" in u]
    for u in eis_candidates:
        if "/epz/order/notice/" in u and "regNumber=" in u:
            eis = u
            break
    if eis is None and eis_candidates:
        eis = eis_candidates[0]

    # Gosplan
    for u in urls:
        if "gosplan" in u:
            gosplan = u
            break

    other = [u for u in urls if u not in {eis, gosplan}]
    # etp отдельно (и не дублируем)
    if etp_url_str and etp_url_str in other:
        other = [u for u in other if u != etp_url_str]

    return {
        "eis": eis,
        "gosplan": gosplan,
        "etp": etp_url_str,
        "other": other,
    }


def format_purchase_summary(purchase: PurchaseListItem) -> str:
    """Краткое текстовое представление закупки."""
    stage_map = {
        1: "подача заявок",
        2: "работа комиссии",
        3: "закупка завершена",
        4: "закупка отменена",
    }

    close_at_str = (
        purchase.submission_close_at.isoformat()
        if purchase.submission_close_at
        else "нет данных"
    )
    max_price_str = (
        f"{purchase.max_price:,.2f}".replace(",", " ")
        if purchase.max_price
        else "нет данных"
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
    """Подробное описание закупки с приложениями, местами поставки и ЯВНЫМИ ссылками."""
    lines = [
        f"Номер закупки: {purchase.purchase_number} ({purchase.law})",
        f"Название: {purchase.title or purchase.short_description or 'нет данных'}",
        f"Заказчик: {purchase.customer.full_name or purchase.customer.short_name or 'нет данных'}",
        f"НМЦК: {purchase.price.initial_price:,.2f} {purchase.price.currency_code}".replace(",", " "),
    ]

    if purchase.timeline.applications_end:
        lines.append(f"Окончание подачи заявок: {purchase.timeline.applications_end.isoformat()}")
    if purchase.timeline.published_at:
        lines.append(f"Опубликовано: {purchase.timeline.published_at.isoformat()}")

    if purchase.classifiers:
        classifier_text = ", ".join(
            f"{c.code}{' (' + c.name + ')' if getattr(c, 'name', None) else ''} [{c.system}]"
            for c in purchase.classifiers
        )
        lines.append(f"Классификаторы: {classifier_text}")

    if purchase.delivery_locations:
        lines.append("Места поставки:")
        for loc in purchase.delivery_locations:
            parts = [loc.region_name or str(loc.region_code or ""), loc.locality_name, loc.raw_address]
            address = ", ".join([p for p in parts if p]) or "нет данных"
            lines.append(f"  - {address}")

    if purchase.objects:
        lines.append("Объекты закупки:")
        for obj in purchase.objects:
            codes = ", ".join(
                f"{c.system}:{c.code}" for c in (obj.classifiers or [])
                if getattr(c, "code", None)
            )
            q = f", qty={obj.quantity:g}" if obj.quantity is not None else ""
            u = f" {obj.quantity_unit_name or ''}".strip()
            lines.append(f"  - {obj.name or 'позиция'}{q}{(' ' + u) if u else ''}" + (f" [{codes}]" if codes else ""))

    if purchase.attachments:
        lines.append(f"Документы ({len(purchase.attachments)}):")
        for attachment in purchase.attachments:
            lines.append(
                f"  - {attachment.file_name} ({attachment.kind_name or 'документ'}) — {attachment.url}"
            )

    if purchase.plan_numbers:
        lines.append(f"Планы: {', '.join(purchase.plan_numbers)}")

    # --- ЯВНЫЕ ссылки (главный фикс против галлюцинаций URL) ---
    urls = classify_urls(
        purchase.card_urls,
        purchase.platform.etp_url if purchase.platform else None,
    )
    if urls.get("eis") or urls.get("gosplan") or urls.get("etp") or urls.get("other"):
        lines.append("Ссылки:")
        if urls.get("eis"):
            lines.append(f"  - ЕИС: {urls['eis']}")
        if urls.get("gosplan"):
            lines.append(f"  - ГосПлан: {urls['gosplan']}")
        if urls.get("etp"):
            lines.append(f"  - ЭТП: {urls['etp']}")
        for u in urls.get("other") or []:
            lines.append(f"  - {u}")

    return "\n".join(lines)


def extract_customer_info(doc: dict[str, Any]) -> CustomerInfo:
    """Извлекает информацию о заказчике из документа источника (с фолбэками по структурам 44/223)."""

    resp_block = doc.get("purchaseResponsibleInfo") or {}
    resp_org = resp_block.get("responsibleOrgInfo") or {}
    resp_info = resp_block.get("responsibleInfo") or {}

    # Иногда заказчик есть в doc.customer.mainInfo, иногда только в responsibleOrgInfo
    main_info = _safe_get(doc, "customer", "mainInfo") or resp_org or {}

    return CustomerInfo(
        inn=_pick(main_info, "inn", "INN"),
        kpp=_pick(main_info, "kpp", "KPP"),
        ogrn=_pick(main_info, "ogrn", "OGRN"),
        full_name=_pick(main_info, "fullName", "fullname"),
        short_name=_pick(main_info, "shortName", "shortname"),
        customer_reg_num=_pick(main_info, "iko", "IKO", "regNum", "customerRegNum"),
        region_name=_pick(main_info, "regionName"),
        legal_address=_pick(main_info, "legalAddress", "factAddress") or _pick(resp_org, "factAddress"),
        postal_address=_pick(main_info, "postalAddress", "postAddress") or _pick(resp_org, "postAddress"),
        email=_pick(main_info, "email", "EMail")
        or _pick(resp_info, "contactEMail", "contactEmail", "email"),
        phone=_pick(main_info, "phone") or _pick(resp_info, "contactPhone", "phone"),
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


def extract_delivery_locations(raw: dict[str, Any], doc: dict[str, Any] | None = None) -> list[LocationInfo]:
    """
    Места поставки:
    - из raw.delivery_places / raw.delivery_places_kladr
    - плюс адреса GAR из деталей (внутри doc), если они есть
    """
    locations: list[LocationInfo] = []

    for place in raw.get("delivery_places", []) or []:
        locations.append(LocationInfo(raw_address=str(place)))

    for kladr in raw.get("delivery_places_kladr", []) or []:
        locations.append(LocationInfo(kladr_or_okato=str(kladr)))

    if doc:
        # Часто адреса живут в deliveryPlacesInfo/byGARInfo/.../GARAddress
        delivery_places_info = (
            _safe_get(doc, "notificationInfo", "customerRequirementsInfo", "customerRequirementInfo", "contractConditionsInfo", "deliveryPlacesInfo")
            or _safe_get(doc, "notificationInfo", "contractConditionsInfo", "deliveryPlacesInfo")
            or {}
        )
        gar_addresses = _walk_collect_values_for_key(delivery_places_info, "GARAddress")
        for addr in gar_addresses:
            if isinstance(addr, str) and addr.strip():
                locations.append(LocationInfo(raw_address=addr.strip()))

    # дедуп по raw_address/kladr_or_okato
    uniq: list[LocationInfo] = []
    seen_keys: set[str] = set()
    for loc in locations:
        k = (loc.raw_address or "").strip() or (loc.kladr_or_okato or "").strip()
        if not k or k in seen_keys:
            continue
        seen_keys.add(k)
        uniq.append(loc)

    return uniq


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
    """
    Позиции закупки (44-ФЗ часто отдаёт структуру через notDrugPurchaseObjectsInfo/drugPurchaseObjectsInfo).
    """
    purchase_objects_info = _safe_get(doc, "notificationInfo", "purchaseObjectsInfo") or {}

    container = None
    if isinstance(purchase_objects_info, dict):
        container = (
            purchase_objects_info.get("notDrugPurchaseObjectsInfo")
            or purchase_objects_info.get("drugPurchaseObjectsInfo")
            or purchase_objects_info
        )
    else:
        container = {}

    purchase_objects = None
    if isinstance(container, dict):
        purchase_objects = container.get("purchaseObject") or container.get("purchaseObjects") or container.get("purchaseObjectInfo")

    objects: list[PurchaseObjectItem] = []
    iterable = _as_list(purchase_objects)

    for obj in iterable:
        if not isinstance(obj, dict):
            continue

        classifiers: list[ClassifierCode] = []

        # KTRU/OKPD2 из KTRU (как в твоём примере)
        ktru = obj.get("KTRU") if isinstance(obj.get("KTRU"), dict) else None
        if ktru:
            classifiers.append(
                ClassifierCode(system="KTRU", code=ktru.get("code", ""), name=ktru.get("name"))
            )
            okpd = ktru.get("OKPD2") if isinstance(ktru.get("OKPD2"), dict) else None
            if okpd and okpd.get("OKPDCode"):
                classifiers.append(
                    ClassifierCode(system="OKPD2", code=okpd.get("OKPDCode", ""), name=okpd.get("OKPDName"))
                )

        # Иногда OKPD2 лежит прямо в obj.OKPD2Info/OKPD2 и т.п. (бережно)
        okpd_code = _safe_get(obj, "OKPD2", "OKPDCode") or _safe_get(obj, "OKPD2Info", "OKPD2", "OKPDCode")
        okpd_name = _safe_get(obj, "OKPD2", "OKPDName") or _safe_get(obj, "OKPD2Info", "OKPD2", "OKPDName")
        if okpd_code and not any(c.system == "OKPD2" and c.code == okpd_code for c in classifiers):
            classifiers.append(ClassifierCode(system="OKPD2", code=str(okpd_code), name=str(okpd_name) if okpd_name else None))

        q_val = None
        if isinstance(obj.get("quantity"), dict):
            q_val = _pick(obj.get("quantity"), "value", "val")
        elif obj.get("quantity") not in (None, "", {}):
            q_val = obj.get("quantity")

        objects.append(
            PurchaseObjectItem(
                name=obj.get("name"),
                classifiers=classifiers,
                ktru_code=ktru.get("code") if ktru else None,
                quantity=float(q_val) if q_val not in (None, "") else None,
                quantity_unit_code=_pick(obj.get("OKEI"), "code") if isinstance(obj.get("OKEI"), dict) else None,
                quantity_unit_name=_pick(obj.get("OKEI"), "name") if isinstance(obj.get("OKEI"), dict) else None,
                price_per_unit=float(obj.get("price")) if obj.get("price") else None,
                total_sum=float(obj.get("sum")) if obj.get("sum") else None,
                object_type=obj.get("type"),
            )
        )

    return objects


def build_purchase_features(raw: dict[str, Any], law: LawLiteral) -> PurchaseFeatures:
    """Собирает нормализованную модель PurchaseFeatures из ответа API."""
    doc = (raw.get("docs") or [{}])[0].get("source", {}) if raw.get("docs") else {}

    # --- классификаторы/объекты/вложения/поставка ---
    classifiers = extract_classifiers(raw.get("okpd2") or [])
    objects = extract_objects(doc)
    attachments = extract_attachments(doc)
    locations = extract_delivery_locations(raw, doc=doc)

    # --- цена ---
    price = PriceInfo(
        currency_code=raw.get("currency_code", "RUB"),
        initial_price=float(raw.get("max_price") or 0.0),
        contract_guarantee_amount=raw.get("contract_guarantee_amount"),
        contract_guarantee_part=raw.get("contract_guarantee_part"),
    )

    # --- даты (самый частый источник потерь качества фильтра) ---
    published_raw = raw.get("published_at")
    published_doc = _safe_get(doc, "commonInfo", "publishDTInEIS") or _safe_get(doc, "commonInfo", "plannedPublishDate")
    published_at = parse_datetime(published_raw) or parse_datetime(published_doc)

    collecting_end = (
        raw.get("submission_close_at")
        or _safe_get(doc, "notificationInfo", "procedureInfo", "collectingInfo", "endDT")
        or raw.get("collecting_finished_at")
    )

    timeline = TimelineInfo(
        published_at=published_at,
        updated_at=parse_datetime(raw.get("updated_at")) or parse_datetime(_safe_get(doc, "commonInfo", "directDT")),
        applications_end=parse_datetime(collecting_end),
        collecting_finished_at=parse_datetime(raw.get("collecting_finished_at")),
    )

    # --- требования/преференции (44-ФЗ часто кладёт в preferenseRequirementInfo) ---
    req_container = _safe_get(doc, "notificationInfo", "requirementsInfo") or {}
    req_items = _as_list(
        (req_container.get("requirementInfo") if isinstance(req_container, dict) else None)
        or (req_container.get("requirement") if isinstance(req_container, dict) else None)
    )
    requirements: list[RequirementInfo] = []
    for item in req_items:
        if not isinstance(item, dict):
            continue
        pr = item.get("preferenseRequirementInfo") if isinstance(item.get("preferenseRequirementInfo"), dict) else {}
        code = _pick(pr, "shortName", "code") or _pick(item, "shortName", "code")
        name = _pick(pr, "name") or _pick(item, "name")
        if code or name:
            requirements.append(RequirementInfo(name=name or "Требование", code=code))

    pref_container = _safe_get(doc, "notificationInfo", "preferensesInfo") or {}
    pref_items = _as_list(
        (pref_container.get("preferenseInfo") if isinstance(pref_container, dict) else None)
        or (pref_container.get("preferense") if isinstance(pref_container, dict) else None)
    )
    preferences: list[PreferenceInfo] = []
    for item in pref_items:
        if not isinstance(item, dict):
            continue
        pr = item.get("preferenseRequirementInfo") if isinstance(item.get("preferenseRequirementInfo"), dict) else {}
        code = _pick(pr, "shortName", "code") or _pick(item, "shortName", "code")
        name = _pick(pr, "name") or _pick(item, "name")
        if code or name:
            preferences.append(PreferenceInfo(name=name or "Преимущество", code=code))

    # --- ссылки на карточки ---
    card_candidates = [
        raw.get("card_url"),
        _safe_get(doc, "commonInfo", "href"),
        _safe_get(doc, "printFormInfo", "url"),
    ]
    card_urls = _uniq_preserve_order([u for u in card_candidates if isinstance(u, str) and u.strip()])

    # --- контактное лицо (в extra, чтобы не ломать модель CustomerInfo) ---
    contact_person = _safe_get(doc, "purchaseResponsibleInfo", "responsibleInfo", "contactPersonInfo") or {}
    contact_fio = None
    if isinstance(contact_person, dict):
        contact_fio = " ".join(
            [p for p in [contact_person.get("lastName"), contact_person.get("firstName"), contact_person.get("middleName")] if p]
        ) or None

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
        requirements=requirements,
        preferences=preferences,
        sme_only=None,
        sme_preference=None,
        card_urls=card_urls,
        attachments=attachments,
        extra={
            "raw": raw,
            "contact_person_fio": contact_fio,
        },
    )


def filter_and_slice_results(
    purchases: List[PurchaseListItem],
    params: SearchPurchasesParams,
    limit: int,
) -> List[PurchaseListItem]:
    """Применяет клиентские фильтры и ограничение по количеству."""
    filtered: list[PurchaseListItem] = []
    for item in purchases:
        if params.region_codes and item.region is not None and item.region not in params.region_codes:
            continue
        if params.collecting_finished_after and item.submission_close_at:
            if item.submission_close_at <= params.collecting_finished_after:
                continue
        if params.collecting_finished_before and item.submission_close_at:
            if item.submission_close_at >= params.collecting_finished_before:
                continue
        filtered.append(item)
        if len(filtered) >= limit:
            break

    return filtered
