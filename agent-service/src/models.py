from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class Okpd2Item(BaseModel):
    code: str
    title: str


class CompanyProfileBase(BaseModel):
    name: str
    description: str

    regions: list[str]
    min_contract_price: float | None = None
    max_contract_price: float | None = None

    industries: list[str]
    resources: dict[str, Any]
    risk_tolerance: Literal["low", "medium", "high"] | None = None

    okpd2_codes: list[Okpd2Item] = Field(default_factory=list)


class CompanyProfileDB(CompanyProfileBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
