from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


FIELD_ORDER: List[str] = [
    "name",
    "description",
    "regions",
    "min_contract_price",
    "max_contract_price",
    "industries",
    "resources",
    "risk_tolerance",
]


def _parse_list_value(raw: str) -> List[str]:
    if raw is None:
        return []
    # допускаем разделение запятыми/точками с запятой/переносами строк
    parts = [p.strip() for p in re.split(r"[\n;,]", str(raw)) if p.strip()]
    return parts


@dataclass
class CompanyFacts:
    """Накопленные факты о компании в рамках одной сессии."""

    name: Optional[str] = None
    description: Optional[str] = None
    regions: List[str] = field(default_factory=list)
    min_contract_price: Optional[float] = None
    max_contract_price: Optional[float] = None
    industries: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    risk_tolerance: Optional[str] = None  # low / medium / high
    okpd2_codes: List[str] = field(default_factory=list)

    def is_field_filled(self, field_name: str) -> bool:
        value = getattr(self, field_name, None)
        if isinstance(value, list):
            return len(value) > 0
        return value not in (None, "")

    def all_required_filled(self) -> bool:
        return all(self.is_field_filled(field_name) for field_name in FIELD_ORDER)

    def set_field_value(self, field_name: str, raw_value: str) -> bool:
        if raw_value is None:
            return False

        raw_value = str(raw_value).strip()
        if not raw_value:
            return False

        if field_name in {"regions", "industries", "resources", "okpd2_codes"}:
            parsed = _parse_list_value(raw_value)
            if not parsed:
                return False
            setattr(self, field_name, parsed)
            return True

        if field_name in {"min_contract_price", "max_contract_price"}:
            try:
                value = float(raw_value.replace(" ", ""))
            except (TypeError, ValueError):
                return False
            setattr(self, field_name, value)
            return True

        if field_name == "risk_tolerance":
            normalized = raw_value.lower()
            setattr(self, field_name, normalized)
            return True

        setattr(self, field_name, raw_value)
        return True

    def next_unfilled_field(self) -> Optional[str]:
        for field_name in FIELD_ORDER:
            if not self.is_field_filled(field_name):
                return field_name
        return None

    def summary(self) -> str:
        def format_value(value: object) -> str:
            if isinstance(value, list):
                return ", ".join(value) if value else "—"
            if value is None:
                return "—"
            return str(value)

        lines = [
            f"Название: {format_value(self.name)}",
            f"Описание: {format_value(self.description)}",
            f"Регионы: {format_value(self.regions)}",
            f"Мин. контракт: {format_value(self.min_contract_price)}",
            f"Макс. контракт: {format_value(self.max_contract_price)}",
            f"Отрасли: {format_value(self.industries)}",
            f"Ресурсы: {format_value(self.resources)}",
            f"Риск: {format_value(self.risk_tolerance)}",
            f"ОКПД2: {format_value(self.okpd2_codes)}",
        ]
        return "\n".join(lines)


# импорт здесь, чтобы избежать циклической зависимости при типизации
import re  # noqa: E402
