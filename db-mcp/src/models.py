from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class Okpd2Item(BaseModel):
    code: str = Field(..., description="ОКПД2 код, например 01.12")
    title: str = Field(..., description="Человеческое название кода")


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

    class Config:
        json_schema_extra = {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "ООО СтройСервис",
                "description": "Строительная компания, специализируется на отделке",
                "regions": ["Москва", "Московская область"],
                "min_contract_price": 500000.0,
                "max_contract_price": 200000000.0,
                "industries": ["строительство"],
                "resources": {"brigades": 3, "equipment": ["вышка", "бетономешалка"]},
                "risk_tolerance": "medium",
                "okpd2_codes": [
                    {"code": "41.20", "title": "Строительство жилых и нежилых зданий"}
                ],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }
