from __future__ import annotations

from uuid import UUID
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


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


LawLiteral = Literal["44-FZ", "223-FZ"]


class SearchPurchasesParams(BaseModel):
    """Параметры поиска закупок для ручки /purchases."""

    classifiers: List[str] = Field(
        default_factory=list,
        description="Коды классификаторов (только ОКПД2 или группы).",
    )
    region_codes: List[int] = Field(
        default_factory=list,
        description="Коды регионов (если пусто, берутся все регионы).",
    )
    collecting_finished_after: Optional[datetime] = Field(
        None,
        description="Искать закупки, где окончание подачи заявок позже указанной даты.",
    )
    collecting_finished_before: Optional[datetime] = Field(
        None,
        description="Искать закупки, где окончание подачи заявок раньше указанной даты.",
    )
    currency_code: Literal["RUB"] = Field(
        "RUB", description="Код валюты контракта; для поискового инструмента всегда RUB."
    )
    sort: Literal["updated_at_desc"] = Field(
        "updated_at_desc",
        description="Фиксированная сортировка от новых обновлений к старым.",
    )
    stage: Literal[1] = Field(
        1,
        description="Этап закупки всегда подача заявок.",
    )
    limit: int = Field(9, ge=1, le=100, description="Максимальное количество записей.")

    @field_validator("classifiers", mode="before")
    @classmethod
    def split_comma_separated(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [code.strip() for code in value.split(",") if code.strip()]
        return list(value)

    @field_validator("region_codes", mode="before")
    @classmethod
    def parse_region_codes(cls, value: Any) -> list[int]:
        if value is None:
            return []
        if isinstance(value, str):
            return [int(code.strip()) for code in value.split(",") if code.strip()]
        return [int(code) for code in value]

class PurchaseListItem(BaseModel):
    """Краткая карточка закупки из /purchases."""

    purchase_number: str
    object_info: Optional[str] = None
    max_price: Optional[float] = None
    currency_code: str = Field("RUB", min_length=3, max_length=3)
    submission_close_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    region: Optional[int] = None
    okpd2: List[str] = Field(default_factory=list)
    stage: Optional[int] = None
    law: LawLiteral

    model_config = {
        "extra": "allow",
    }


class ClassifierCode(BaseModel):
    """Универсальное представление кода из классификатора: ОКПД2, ОКВЭД2, КТРУ, КВР."""

    system: Literal["OKPD2", "OKVED2", "KTRU", "KVR", "OTHER"] = Field(
        ..., description="Тип классификатора (ОКПД2, ОКВЭД2, КТРУ, КВР и т.п.)."
    )
    code: str = Field(..., description="Код по классификатору (например, '62.02.3').")
    name: Optional[str] = Field(None, description="Человеческое название кода, если доступно.")


class LocationInfo(BaseModel):
    """Нормализованная информация о месте исполнения / поставки."""

    country_code: Optional[str] = Field(None, description="Код страны (например, '643').")
    country_name: Optional[str] = Field(None, description="Название страны.")
    region_code: Optional[str] = Field(
        None,
        description="Код региона по источнику (например '50', '77').",
    )
    region_name: Optional[str] = Field(None, description="Название региона.")
    federal_district: Optional[str] = Field(None, description="Федеральный округ, если есть.")
    locality_name: Optional[str] = Field(None, description="Название муниципалитета / города / района.")
    kladr_or_okato: Optional[str] = Field(
        None, description="КЛАДР / ОКАТО / ГАР-код или аналогичный идентификатор места."
    )
    raw_address: Optional[str] = Field(None, description="Полный текст адреса как есть в источнике.")


class TimelineInfo(BaseModel):
    """Сводная временная информация по лоту / закупке."""

    published_at: Optional[datetime] = Field(None, description="Дата/время публикации извещения.")
    updated_at: Optional[datetime] = Field(None, description="Дата/время последнего обновления.")
    applications_start: Optional[datetime] = Field(None, description="Начало подачи заявок.")
    applications_end: Optional[datetime] = Field(None, description="Окончание подачи заявок (крайний срок).")
    collecting_finished_at: Optional[datetime] = Field(
        None, description="Дата/время завершения сбора заявок (если источник так это называет)."
    )
    bidding_datetime: Optional[datetime] = Field(
        None, description="Дата/время проведения аукциона / торгов, если применимо."
    )
    summarizing_datetime: Optional[datetime] = Field(
        None, description="Дата/время подведения итогов, если задана."
    )
    contract_start: Optional[date] = Field(None, description="Плановая дата начала исполнения контракта.")
    contract_end: Optional[date] = Field(None, description="Плановая дата окончания исполнения контракта.")


class PriceInfo(BaseModel):
    """Денежные параметры лота (НМЦК, обеспечения, финансирование)."""

    currency_code: str = Field(..., description="Код валюты в формате ISO (например, 'RUB').")
    initial_price: float = Field(..., description="Начальная (максимальная) цена контракта по лоту.")
    application_guarantee_amount: Optional[float] = Field(
        None, description="Размер обеспечения заявки в валюте лота."
    )
    application_guarantee_part: Optional[float] = Field(
        None, description="Доля обеспечения заявки в процентах от НМЦК."
    )
    contract_guarantee_amount: Optional[float] = Field(
        None, description="Размер обеспечения исполнения контракта."
    )
    contract_guarantee_part: Optional[float] = Field(
        None, description="Доля обеспечения контракта в процентах от НМЦК."
    )
    financing_total: Optional[float] = Field(None, description="Общий объём финансирования по лоту.")
    financing_by_year: Dict[int, float] = Field(
        default_factory=dict, description="Разбивка финансирования по годам: {год: сумма}."
    )
    self_funds: Optional[bool] = Field(None, description="Финансирование за счёт собственных средств заказчика.")


class CustomerInfo(BaseModel):
    """Нормализованный профиль заказчика."""

    inn: Optional[str] = Field(None, description="ИНН заказчика.")
    kpp: Optional[str] = Field(None, description="КПП заказчика.")
    ogrn: Optional[str] = Field(None, description="ОГРН заказчика.")
    full_name: Optional[str] = Field(None, description="Полное наименование заказчика.")
    short_name: Optional[str] = Field(None, description="Сокращённое наименование заказчика.")
    customer_reg_num: Optional[str] = Field(None, description="Регистрационный номер заказчика в ЕИС / реестре.")
    region_name: Optional[str] = Field(None, description="Регион, указанный у заказчика.")
    legal_address: Optional[str] = Field(None, description="Юридический адрес заказчика.")
    postal_address: Optional[str] = Field(None, description="Почтовый адрес заказчика.")
    email: Optional[str] = Field(None, description="Контактный e-mail заказчика или ответственного лица.")
    phone: Optional[str] = Field(None, description="Контактный телефон.")


class PlatformInfo(BaseModel):
    """Информация о площадке и способе закупки."""

    law: Literal["44-FZ", "223-FZ", "OTHER"] = Field(
        ..., description="Режим закупки (44-ФЗ, 223-ФЗ и т.п.)."
    )
    placing_way_code: Optional[str] = Field(None, description="Код способа определения поставщика.")
    placing_way_name: Optional[str] = Field(None, description="Название способа закупки.")
    etp_code: Optional[str] = Field(None, description="Код электронной площадки.")
    etp_name: Optional[str] = Field(None, description="Название электронной площадки.")
    etp_url: Optional[HttpUrl] = Field(None, description="URL площадки.")
    is_electronic: Optional[bool] = Field(None, description="Признак электронной формы проведения закупки.")


class AttachmentInfo(BaseModel):
    """Любой файл/документ, прикреплённый к закупке."""

    uid: Optional[str] = Field(None, description="Идентификатор документа в источнике.")
    kind_code: Optional[str] = Field(None, description="Код типа документа.")
    kind_name: Optional[str] = Field(None, description="Название типа документа.")
    file_name: str = Field(..., description="Имя файла.")
    description: Optional[str] = Field(None, description="Текстовое описание документа.")
    url: HttpUrl = Field(..., description="Ссылка на скачивание файла.")
    size_bytes: Optional[int] = Field(None, description="Размер файла в байтах, если известен.")
    doc_date: Optional[datetime] = Field(None, description="Дата документа (как в ЕИС).")


class RequirementInfo(BaseModel):
    """Требования и ограничения к участникам."""

    code: Optional[str] = Field(None, description="Краткий код/шифр требования.")
    name: str = Field(..., description="Описание требования.")


class PreferenceInfo(BaseModel):
    """Преимущества, преференции (СМП/СОНКО и т.п.)."""

    code: Optional[str] = Field(None, description="Код преференции.")
    name: str = Field(..., description="Описание преференции.")


class PurchaseObjectItem(BaseModel):
    """Конкретный объект закупки в рамках лота."""

    name: Optional[str] = Field(None, description="Наименование объекта.")
    classifiers: List[ClassifierCode] = Field(
        default_factory=list, description="Связанные коды (ОКПД2, КТРУ, ОКВЭД2 и т.п.)."
    )
    ktru_code: Optional[str] = Field(None, description="Код КТРУ (если есть).")
    quantity: Optional[float] = Field(None, description="Количество по позиции.")
    quantity_unit_code: Optional[str] = Field(None, description="Код единицы измерения.")
    quantity_unit_name: Optional[str] = Field(None, description="Название единицы измерения.")
    price_per_unit: Optional[float] = Field(None, description="Цена за единицу.")
    total_sum: Optional[float] = Field(None, description="Общая сумма по позиции.")
    object_type: Optional[str] = Field(None, description="Тип объекта: товар/работа/услуга.")


class PurchaseFeatures(BaseModel):
    """Нормализованная сущность «лот/закупка для рекомендаций».

    Единица для скоринга — один лот (или вся закупка, если она безлотовая).
    """

    source_system: Literal["GOSPLAN", "EIS", "OTHER"] = Field(
        ..., description="Источник данных (агрегация ГосПлан, прямая ЕИС и т.п.)."
    )
    law: Literal["44-FZ", "223-FZ", "OTHER"] = Field(
        ..., description="Режим закупки (44-ФЗ, 223-ФЗ и т.п.)."
    )
    purchase_number: str = Field(..., description="Номер закупки (регистрационный номер извещения).")
    lot_number: Optional[str] = Field(None, description="Номер лота (если закупка лотовая).")
    lot_internal_id: Optional[str] = Field(None, description="Внутренний идентификатор лота/позиции.")
    ikz: Optional[str] = Field(None, description="ИКЗ / код идентификации закупки (если есть).")
    plan_numbers: List[str] = Field(default_factory=list, description="Регистрационные номера планов.")
    plan_position_numbers: List[str] = Field(
        default_factory=list, description="Номера позиций в плане по данному лоту."
    )
    title: Optional[str] = Field(None, description="Краткое наименование закупки/лота.")
    short_description: Optional[str] = Field(None, description="Краткая выжимка сути закупки.")
    extended_description: Optional[str] = Field(None, description="Более развёрнутое описание.")
    stage: Optional[int] = Field(None, description="Стадия закупки по данным источника.")
    status: Optional[str] = Field(None, description="Статус закупки/лота.")
    is_cancelled: Optional[bool] = Field(None, description="Признак отмены закупки/лота.")
    customer: CustomerInfo = Field(..., description="Нормализованный профиль заказчика.")
    platform: PlatformInfo = Field(..., description="Информация о площадке и способе закупки.")
    delivery_locations: List[LocationInfo] = Field(
        default_factory=list, description="Список мест исполнения / поставки."
    )
    timeline: TimelineInfo = Field(..., description="Сводная временная информация по лоту.")
    price: PriceInfo = Field(..., description="Финансовые параметры лота.")
    classifiers: List[ClassifierCode] = Field(
        default_factory=list, description="Все связанные коды по лоту."
    )
    objects: List[PurchaseObjectItem] = Field(
        default_factory=list, description="Список конкретных позиций закупки."
    )
    requirements: List[RequirementInfo] = Field(
        default_factory=list, description="Требования к участникам."
    )
    preferences: List[PreferenceInfo] = Field(
        default_factory=list, description="Преимущества (СМП/СОНКО и т.п.)."
    )
    sme_only: Optional[bool] = Field(None, description="Закупка только для СМП/СОНКО.")
    sme_preference: Optional[bool] = Field(None, description="Есть ли преимущество для СМП/СОНКО.")
    card_urls: List[HttpUrl] = Field(default_factory=list, description="Ссылки на карточки закупки.")
    attachments: List[AttachmentInfo] = Field(
        default_factory=list, description="Все прикреплённые документы."
    )
    extra: Dict[str, Any] = Field(default_factory=dict, description="Произвольные дополнительные поля источника.")

