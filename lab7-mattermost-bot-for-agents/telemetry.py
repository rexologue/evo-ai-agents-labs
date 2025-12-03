"""Настройка OpenInference и OpenTelemetry телеметрии."""
import logging
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from openinference.instrumentation import OpenInferenceInstrumentor

from config import config

logger = logging.getLogger(__name__)

_tracer: Optional[trace.Tracer] = None
_instrumented: bool = False


def setup_telemetry() -> trace.Tracer:
    """
    Настройка OpenTelemetry и OpenInference телеметрии.

    Returns:
        Tracer для создания spans
    """
    global _tracer, _instrumented

    if _tracer is not None:
        return _tracer

    try:
        # Создаем ресурс с информацией о сервисе
        resource = Resource.create(
            {
                "service.name": config.OTEL_SERVICE_NAME,
                "service.type": "mattermost-bot",
            }
        )

        # Настраиваем TracerProvider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)

        # Настраиваем OTLP экспортер
        otlp_exporter = OTLPSpanExporter(
            endpoint=config.OTEL_EXPORTER_OTLP_ENDPOINT,
        )

        # Добавляем BatchSpanProcessor для эффективной отправки spans
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)

        # Получаем tracer
        _tracer = trace.get_tracer(__name__)

        # Инструментируем через OpenInference
        if not _instrumented:
            try:
                OpenInferenceInstrumentor().instrument()
                _instrumented = True
                logger.info("OpenInference инструментация активирована")
            except Exception as e:
                logger.warning(f"Не удалось активировать OpenInference: {e}")

        logger.info(
            f"Телеметрия настроена: endpoint={config.OTEL_EXPORTER_OTLP_ENDPOINT}, "
            f"service={config.OTEL_SERVICE_NAME}"
        )

        return _tracer

    except Exception as e:
        logger.error(f"Ошибка настройки телеметрии: {e}")
        # Возвращаем no-op tracer если настройка не удалась
        return trace.NoOpTracer()


def get_tracer() -> trace.Tracer:
    """
    Получить tracer для создания spans.

    Returns:
        Tracer instance
    """
    if _tracer is None:
        return setup_telemetry()
    return _tracer


def create_span(
    name: str,
    attributes: Optional[dict] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
) -> trace.Span:
    """
    Создать новый span с заданными атрибутами.

    Args:
        name: Имя span
        attributes: Словарь атрибутов для span
        kind: Тип span

    Returns:
        Созданный span
    """
    tracer = get_tracer()
    span = tracer.start_span(name, kind=kind)

    if attributes:
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, str(value))

    return span


def set_span_attribute(span: trace.Span, key: str, value: any) -> None:
    """
    Установить атрибут span.

    Args:
        span: Span для установки атрибута
        key: Ключ атрибута
        value: Значение атрибута
    """
    if span and value is not None:
        try:
            span.set_attribute(key, str(value))
        except Exception as e:
            logger.warning(f"Не удалось установить атрибут {key}: {e}")


