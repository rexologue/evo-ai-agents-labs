"""Инструмент для поиска государственных закупок по 223-ФЗ."""

from datetime import datetime

import httpx
from fastmcp import Context
from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field, ValidationError

from ..mcp_instance import mcp
from ..metrics import API_CALLS
from .models import PurchaseIndex, SearchPurchasesRequest
from .utils import ToolResult, format_api_error, format_purchase_list

tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="search_purchases",
    description="""🔍 Поиск государственных закупок по 223-ФЗ

Ищет закупки в системе ГосПлан, по которым можно подавать заявки на участие.

Параметры поиска:
- classifier: Код ОКПД2 (например, "26.20.11.110" для компьютеров)
- submission_close_after: Найти закупки с окончанием подачи заявок ПОСЛЕ этой даты (ISO format)
- submission_close_before: Найти закупки с окончанием подачи заявок ДО этой даты (ISO format)
- region: Код региона (например, 77 для Москвы)
- limit: Количество результатов (1-100, по умолчанию 20)
- skip: Пропустить первые N результатов (для пагинации)

По умолчанию ищет закупки на этапе "подача заявок" (stage=1) в рублях (RUB).
""",
)
async def search_purchases(
    ctx: Context,
    classifier: str | None = Field(None, description="Код ОКПД2"),
    submission_close_after: str | None = Field(
        None, description="ISO datetime"
    ),
    submission_close_before: str | None = Field(
        None, description="ISO datetime"
    ),
    region: int | None = Field(None, description="Код региона (1-99)"),
    limit: int = Field(20, ge=1, le=100),
    skip: int = Field(0, ge=0),
) -> ToolResult:
    """
    Поиск государственных закупок по 223-ФЗ.

    Args:
        classifier: Код ОКПД2
        submission_close_after: Дата окончания подачи заявок (после)
        submission_close_before: Дата окончания подачи заявок (до)
        region: Код региона
        limit: Количество результатов
        skip: Пропустить первые N результатов
        ctx: Контекст для логирования

    Returns:
        ToolResult: Результаты поиска

    Raises:
        McpError: При ошибках выполнения
    """
    with tracer.start_as_current_span("search_purchases") as span:
        span.set_attribute("classifier", classifier or "all")
        span.set_attribute("region", region or "all")
        span.set_attribute("limit", limit)
        span.set_attribute("skip", skip)

        await ctx.info("🔍 Начинаем поиск государственных закупок")
        await ctx.report_progress(progress=0, total=100)

        API_CALLS.labels(
            service="gosplan", endpoint="search_purchases", status="started"
        ).inc()

        try:
            # Этап 1: Валидация и подготовка (0-25%)
            await ctx.info(
                f"🔧 Параметры поиска: ОКПД2={classifier or 'все'}, "
                f"регион={region or 'все'}"
            )

            # Преобразование строк datetime в объекты datetime
            try:
                close_after = (
                    datetime.fromisoformat(submission_close_after)
                    if submission_close_after
                    else None
                )
                close_before = (
                    datetime.fromisoformat(submission_close_before)
                    if submission_close_before
                    else None
                )

                request_params = SearchPurchasesRequest(
                    classifier=classifier,
                    submission_close_after=close_after,
                    submission_close_before=close_before,
                    region=region,
                    stage=1,  # Всегда ищем закупки на этапе подачи заявок
                    currency_code="RUB",  # Всегда ищем в рублях
                    limit=limit,
                    skip=skip,
                )
            except ValueError as e:
                span.set_attribute("error", "validation_error")
                await ctx.error(f"❌ Неверные параметры: {e}")
                raise McpError(
                    ErrorData(code=-32602, message=f"Неверные параметры: {e}")
                )

            await ctx.report_progress(progress=25, total=100)

            # Этап 2: Выполнение запроса к API (25-75%)
            await ctx.info("📡 Отправляем запрос к API ГосПлан")
            await ctx.report_progress(progress=50, total=100)

            # Формируем параметры запроса (исключаем None)
            query_params = {
                k: v
                for k, v in {
                    "classifier": request_params.classifier,
                    "submission_close_after": (
                        request_params.submission_close_after.isoformat()
                        if request_params.submission_close_after
                        else None
                    ),
                    "submission_close_before": (
                        request_params.submission_close_before.isoformat()
                        if request_params.submission_close_before
                        else None
                    ),
                    "region": request_params.region,
                    "stage": request_params.stage,
                    "currency_code": request_params.currency_code,
                    "limit": request_params.limit,
                    "skip": request_params.skip,
                }.items()
                if v is not None
            }

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    "https://v2test.gosplan.info/fz223/purchases",
                    params=query_params,
                )
                response.raise_for_status()
                purchases_data = response.json()

            await ctx.report_progress(progress=75, total=100)

            # Этап 3: Обработка результатов (75-100%)
            await ctx.info("📄 Обрабатываем результаты поиска")

            # Парсим ответ с использованием Pydantic
            try:
                purchases = [
                    PurchaseIndex(**p) for p in purchases_data
                ]
            except ValidationError as e:
                span.set_attribute("error", "parse_error")
                await ctx.error(f"❌ Ошибка парсинга ответа API: {e}")
                API_CALLS.labels(
                    service="gosplan",
                    endpoint="search_purchases",
                    status="error",
                ).inc()
                raise McpError(
                    ErrorData(
                        code=-32603,
                        message=f"Ошибка обработки ответа API: {e}",
                    )
                )

            # Форматируем для LLM
            formatted_text = format_purchase_list(
                purchases=[p.model_dump() for p in purchases],
                total=len(purchases),
            )

            await ctx.report_progress(progress=100, total=100)
            await ctx.info(f"✅ Найдено закупок: {len(purchases)}")

            span.set_attribute("success", True)
            span.set_attribute("results_count", len(purchases))

            API_CALLS.labels(
                service="gosplan",
                endpoint="search_purchases",
                status="success",
            ).inc()

            return ToolResult(
                content=[TextContent(type="text", text=formatted_text)],
                structured_content=[p.model_dump() for p in purchases],
                meta={
                    "query_params": query_params,
                    "total_results": len(purchases),
                    "has_more": len(purchases) == limit,
                },
            )

        except httpx.HTTPStatusError as e:
            span.set_attribute("error", "http_status_error")
            span.set_attribute("status_code", e.response.status_code)

            # Специальная обработка 422 (валидация)
            if e.response.status_code == 422:
                error_message = format_api_error(
                    e.response.text, e.response.status_code
                )
                await ctx.error(f"❌ {error_message}")

                API_CALLS.labels(
                    service="gosplan",
                    endpoint="search_purchases",
                    status="error",
                ).inc()

                raise McpError(
                    ErrorData(code=-32602, message=error_message)
                )

            # Остальные HTTP ошибки
            error_message = format_api_error(
                e.response.text if e.response else "",
                e.response.status_code if e.response else 0,
            )

            await ctx.error(f"❌ HTTP ошибка: {error_message}")

            API_CALLS.labels(
                service="gosplan",
                endpoint="search_purchases",
                status="error",
            ).inc()

            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Не удалось выполнить поиск.\n\n{error_message}",
                )
            )

        except httpx.TimeoutException:
            span.set_attribute("error", "timeout")
            await ctx.error("❌ Превышено время ожидания ответа от API")

            API_CALLS.labels(
                service="gosplan",
                endpoint="search_purchases",
                status="error",
            ).inc()

            raise McpError(
                ErrorData(
                    code=-32603,
                    message="Превышено время ожидания ответа от API ГосПлан",
                )
            )

        except httpx.RequestError as e:
            span.set_attribute("error", "request_error")
            await ctx.error(f"❌ Ошибка сети: {e}")

            API_CALLS.labels(
                service="gosplan",
                endpoint="search_purchases",
                status="error",
            ).inc()

            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Ошибка подключения к API ГосПлан: {e}",
                )
            )

        except Exception as e:
            span.set_attribute("error", str(e))
            await ctx.error(f"💥 Неожиданная ошибка: {e}")

            API_CALLS.labels(
                service="gosplan",
                endpoint="search_purchases",
                status="error",
            ).inc()

            raise McpError(
                ErrorData(code=-32603, message=f"Неожиданная ошибка: {e}")
            )
