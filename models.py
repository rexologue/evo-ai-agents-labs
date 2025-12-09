from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, List
from uuid import UUID

from pydantic import BaseModel, Field


class Okpd2Item(BaseModel):
    code: str = Field(..., description="ОКПД2 код, например 01.12")
    title: str = Field(..., description="Человеческое название кода")

    
class CompanyProfileBase(BaseModel):
    """
    Описание входных данных для создания профиля компании.
    Эту модель можно (и стоит) переиспользовать и на стороне MCP.
    """

    name: str = Field(
        ...,
        description="Название компании.",
    )
    description: str = Field(
        ...,
        description="Краткое текстовое описание того, чем занимается компания. На русском.",
    )
    regions: List[str] = Field(
        ...,
        description="Список регионов/городов, где компания фактически работает. На русском (например: 'Красноярск', 'Красноярский край').",
    )
    min_contract_price: float = Field(
        ...,
        description="Минимальная типичная сумма контракта в рублях.",
    )
    max_contract_price: float = Field(
        ...,
        description="Максимальная типичная сумма контракта в рублях.",
    )
    industries: List[str] = Field(
        ...,
        description="Список отраслей/сфер деятельности (например: 'производство мебели', 'установка кухонь', 'розничная торговля'). На русском.",
    )
    resources: List[str] = Field(
        ...,
        description="Ключевые ресурсы компании: цех, команда, сеть магазинов, технологии и т.п. На русском.",
    )
    risk_tolerance: Literal["low", "medium", "high"] = Field(
        ...,
        description=(
            "Уровень толерантности к риску: "
            "'low' — предпочитает стабильность и предсказуемость; "
            "'medium' — допускает умеренный риск; "
            "'high' — готова к высоким рискам ради роста."
        ),
    )
    okpd2_codes: List[Okpd2Item] = Field(
        ...,
        description="Список кодов ОКПД2, соответствующих основной деятельности компании.",
    )


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
