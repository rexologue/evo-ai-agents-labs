"""Pydantic модели для работы с данными ГосПлан."""

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SearchPurchasesRequest(BaseModel):
    """Параметры поиска закупок."""
    classifier: str | None = Field(None, description="Код ОКПД2")

    def validate_okpd2(cls, value: str | None) -> str | None:
        """Проверяет, что код ОКПД2 соответствует формату xx.yy.zz.qq."""

        if value is None:
            return value
        if not re.match(r"^\d{2}(\.\d{2}){0,3}$", value):
            raise ValueError(f"Invalid OKPD2 format: {value}")
        return value
    """Запрос на получение деталей закупки."""

    """Документ из карточки закупки."""
    """Краткая модель закупки из списка."""
    """Детальная модель закупки с полным набором полей."""
    # Наследует все поля PurchaseIndex, включая документы с исходными данными
    # в поле source
        if v is None:
            return v
        if not re.match(r"^\d{2}(\.\d{2}){0,3}$", v):
            raise ValueError(f"Invalid OKPD2 format: {v}")
        return v


class GetPurchaseDetailsRequest(BaseModel):
    """>45;L 20;840F88 ?0@0<5B@>2 4;O ?>;CG5=8O 45B0;59 70:C?:8."""

    purchase_number: str = Field(..., min_length=1)


class PurchaseDocument(BaseModel):
    """>:C<5=B 70:C?:8."""

    doc_type: str
    published_at: datetime
    source: dict[str, Any] | None = None


class PurchaseIndex(BaseModel):
    """07>20O 8=D>@<0F8O > 70:C?:5 (4;O A?8A:0)."""

    submission_close_at: datetime | None = None
    currency_code: str
    customer: str
    delivery_places: list[str] | None = None
    doc_created_at: datetime
    doc_updated_at: datetime
    docs: list[PurchaseDocument]
    max_price: float | None = None
    object_info: str
    okpd2: list[str] | None = None
    region: int
    purchase_number: str
    stage: int
    placer: str | None = None
    plan_numbers: list[str] | None = None
    position_numbers: list[str] | None = None
    published_at: datetime
    purchase_type: str
    updated_at: datetime


class Purchase(PurchaseIndex):
    """>;=0O 8=D>@<0F8O > 70:C?:5 (A 45B0;O<8 4>:C<5=B>2)."""

    # 0A;54C5B 2A5 ?>;O >B PurchaseIndex
    #  docs 1C45B 70?>;=5=> ?>;5 source A ?>;=K<8 40==K<8 4>:C<5=B0
