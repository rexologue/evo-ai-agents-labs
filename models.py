from __future__ import annotations

from uuid import UUID
from datetime import datetime
from typing import Literal, List

from pydantic import BaseModel, Field


class Okpd2Item(BaseModel):
    code: str = Field(..., description="ОКПД2 код, например 01.12")
    title: str = Field(..., description="Человеческое название кода")
    
    
class RegionItem(BaseModel):
    code: str = Field(..., description="Код региона (натуральное число)")
    title: str = Field(..., description="Человеческое название региона")

    
class CompanyProfileBase(BaseModel):
    """
    Описание входных данных для создания профиля компании.
    """

    name: str = Field(
        ...,
        description="Название компании.",
    )
    description: str = Field(
        ...,
        description="Краткое текстовое описание того, чем занимается компания. На русском.",
    )
    regions_codes: List[RegionItem] = Field(
        ...,
        description="Список кодов регионов/городов, где компания фактически работает.",
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
                "description": "Строительная компания, специализируется на отделке в Москве и МО",
                "regions_codes": [
                    {"code": "77", "title": "Город Москва"}, {"code": "50", "title": "Московская область"}
                ],
                "okpd2_codes": [
                    {"code": "41.20", "title": "Строительство жилых и нежилых зданий"}
                ],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }
