from app.observability.metrics import MetricsCollector
from app.observability.events import (
    GatewayEvent,
    ProviderAttemptEvent,
    ProviderFailureEvent,
    ProviderSuccessEvent,
    RequestFinishedEvent,
    RequestStartedEvent,
    RetryEvent,
    FallbackEvent,
)
from app.observability.logger import logger

metrics = MetricsCollector()




def log_event(event: GatewayEvent) -> None:
    if isinstance(event, RequestStartedEvent):
        logger.info(
            "request_started | request_id=%s | team_id=%s",
            event.request_id,
            event.team_id,
        )

    elif isinstance(event, ProviderAttemptEvent):
        logger.info(
            "provider_attempt | request_id=%s | provider=%s | attempt=%s",
            event.request_id,
            event.provider,
            event.attempt,
        )

    elif isinstance(event, ProviderSuccessEvent):
        logger.info(
            "provider_success | request_id=%s | provider=%s | latency_ms=%.2f",
            event.request_id,
            event.provider,
            event.latency_ms,
        )

    elif isinstance(event, ProviderFailureEvent):
        logger.error(
            "provider_failure | request_id=%s | provider=%s | error=%s",
            event.request_id,
            event.provider,
            event.error,
        )

    elif isinstance(event, RetryEvent):
        logger.warning(
            "provider_retry | request_id=%s | provider=%s | attempt=%s",
            event.request_id,
            event.provider,
            event.attempt,
        )

    elif isinstance(event, FallbackEvent):
        logger.warning(
            "provider_fallback | request_id=%s | from=%s | to=%s",
            event.request_id,
            event.from_provider,
            event.to_provider,
        )

    elif isinstance(event, RequestFinishedEvent):
        logger.info(
            "request_finished | request_id=%s | provider=%s | latency_ms=%.2f",
            event.request_id,
            event.provider,
            event.total_latency_ms,
        )
def record_metric(event: GatewayEvent) -> None:

    if isinstance(event, RequestStartedEvent):
        metrics.increment_request()

    elif isinstance(event, ProviderAttemptEvent):
        metrics.increment_provider_attempt(
            event.provider
        )

    elif isinstance(event, ProviderSuccessEvent):
        metrics.record_provider_success(
            provider=event.provider,
            latency_ms=event.latency_ms,
            input_tokens=event.input_tokens,
            output_tokens=event.output_tokens,
        )
        metrics.increment_success()

    elif isinstance(event, ProviderFailureEvent):
        metrics.increment_provider_failure(
            event.provider
        )

    elif isinstance(event, RetryEvent):
        metrics.increment_provider_retry(
            event.provider
        )

    elif isinstance(event, FallbackEvent):
        metrics.increment_provider_fallback(
            event.from_provider
        )