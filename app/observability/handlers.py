from app.observability.metrics import MetricsCollector
from app.observability.prometheus import prometheus_metrics
from app.observability.events import (
    GatewayEvent,
    ProviderAttemptEvent,
    ProviderFailureEvent,
    ProviderSuccessEvent,
    RequestFinishedEvent,
    RequestStartedEvent,
    RetryEvent,
    FallbackEvent,
    StreamFirstTokenEvent,
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
        prometheus_metrics.requests_total.labels(status="started", team_id=event.team_id).inc()

    elif isinstance(event, ProviderAttemptEvent):
        metrics.increment_provider_attempt(event.provider)
        prometheus_metrics.provider_attempts_total.labels(provider=event.provider).inc()

    elif isinstance(event, ProviderSuccessEvent):
        metrics.record_provider_success(
            provider=event.provider,
            latency_ms=event.latency_ms,
            input_tokens=event.input_tokens,
            output_tokens=event.output_tokens,
        )
        metrics.increment_success()
        prometheus_metrics.requests_total.labels(status="success", team_id="default").inc()
        prometheus_metrics.tokens_total.labels(provider=event.provider, type="input").inc(event.input_tokens)
        prometheus_metrics.tokens_total.labels(provider=event.provider, type="output").inc(event.output_tokens)
        prometheus_metrics.stream_duration_seconds.labels(provider=event.provider).observe(event.latency_ms / 1000.0)

    elif isinstance(event, ProviderFailureEvent):
        metrics.increment_provider_failure(event.provider)
        metrics.increment_failure()
        prometheus_metrics.provider_failures_total.labels(provider=event.provider).inc()
        prometheus_metrics.requests_total.labels(status="failed", team_id="default").inc()

    elif isinstance(event, RetryEvent):
        metrics.increment_provider_retry(event.provider)

    elif isinstance(event, FallbackEvent):
        metrics.increment_provider_fallback(event.from_provider)
        prometheus_metrics.fallbacks_total.labels(from_provider=event.from_provider, to_provider=event.to_provider).inc()

    elif isinstance(event, StreamFirstTokenEvent):
        prometheus_metrics.stream_ttft_seconds.labels(provider=event.provider).observe(event.ttft_ms / 1000.0)