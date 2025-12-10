"""Pydantic <>45;8 4;O 20;840F88 70?@>A>2 8 ?0@A8=30 >B25B>2 API >A;0=."""

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SearchPurchasesRequest(BaseModel):
    """>45;L 20;840F88 ?0@0<5B@>2 4;O ?>8A:0 70:C?>:."""

    classifier: str | None = Field(None, description="OKPD2 :>4")
    submission_close_after: datetime | None = None
    submission_close_before: datetime | None = None
    region: int | None = Field(None, ge=1, le=99)
    stage: int = Field(1)
    currency_code: str = Field("RUB")
    limit: int = Field(20, ge=1, le=100)
    skip: int = Field(0, ge=0)

    @field_validator("classifier")
    @classmethod
    def validate_okpd2(cls, v: str | None) -> str | None:
        """0;840F8O D>@<0B0 2: xx.yy.zz.qq 8;8 3@C??K (xx, xx.yy)."""
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
