import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry

from app.main import app
from app.observability.events import (
    FallbackEvent,
    ProviderAttemptEvent,
    ProviderFailureEvent,
    ProviderSuccessEvent,
    RequestStartedEvent,
    StreamFirstTokenEvent,
)
from app.observability.handlers import record_metric
from app.observability.prometheus import PrometheusCollector, prometheus_metrics


def test_prometheus_collector_metric_definitions():
    """Verify clean metric definitions and label dimensions."""
    registry = CollectorRegistry()
    collector = PrometheusCollector(registry=registry)

    # 1. Request counter
    collector.requests_total.labels(status="started", team_id="team-a").inc()
    collector.requests_total.labels(status="success", team_id="team-a").inc()

    # 2. Provider attempts & failures
    collector.provider_attempts_total.labels(provider="nvidia_nim").inc()
    collector.provider_failures_total.labels(provider="nvidia_nim").inc()

    # 3. Fallbacks
    collector.fallbacks_total.labels(from_provider="nvidia_nim", to_provider="openrouter").inc()

    # 4. Token counters
    collector.tokens_total.labels(provider="openrouter", type="input").inc(50)
    collector.tokens_total.labels(provider="openrouter", type="output").inc(120)

    # 5. Circuit Breaker Gauge
    collector.circuit_breaker_state.labels(provider="nvidia_nim").set(1.0)
    collector.circuit_breaker_state.labels(provider="openrouter").set(0.0)

    # 6. Histograms
    collector.stream_ttft_seconds.labels(provider="openrouter").observe(0.42)
    collector.stream_duration_seconds.labels(provider="openrouter").observe(3.5)

    exposition = collector.generate_exposition().decode("utf-8")

    # Assertions
    assert "gateway_requests_total{status=\"started\",team_id=\"team-a\"} 1.0" in exposition
    assert "gateway_provider_attempts_total{provider=\"nvidia_nim\"} 1.0" in exposition
    assert "gateway_provider_failures_total{provider=\"nvidia_nim\"} 1.0" in exposition
    assert "gateway_fallbacks_total{from_provider=\"nvidia_nim\",to_provider=\"openrouter\"} 1.0" in exposition
    assert "gateway_tokens_total{provider=\"openrouter\",type=\"input\"} 50.0" in exposition
    assert "gateway_tokens_total{provider=\"openrouter\",type=\"output\"} 120.0" in exposition
    assert "gateway_circuit_breaker_state{provider=\"nvidia_nim\"} 1.0" in exposition
    assert "gateway_circuit_breaker_state{provider=\"openrouter\"} 0.0" in exposition
    assert "gateway_stream_ttft_seconds_bucket{le=\"0.5\",provider=\"openrouter\"} 1.0" in exposition


def test_provider_label_isolation():
    """Verify metrics from different providers do not overwrite each other."""
    registry = CollectorRegistry()
    collector = PrometheusCollector(registry=registry)

    collector.provider_attempts_total.labels(provider="nvidia_nim").inc(5)
    collector.provider_attempts_total.labels(provider="openrouter").inc(10)
    collector.provider_attempts_total.labels(provider="ollama").inc(3)

    exposition = collector.generate_exposition().decode("utf-8")

    assert "gateway_provider_attempts_total{provider=\"nvidia_nim\"} 5.0" in exposition
    assert "gateway_provider_attempts_total{provider=\"openrouter\"} 10.0" in exposition
    assert "gateway_provider_attempts_total{provider=\"ollama\"} 3.0" in exposition


def test_observability_event_subscription_updates_prometheus():
    """Verify event subscribers trigger prometheus metrics correctly."""
    record_metric(
        RequestStartedEvent(
            request_id="req-1",
            timestamp=datetime.now(),
            event_type="request_started",
            team_id="prom-team",
        )
    )

    record_metric(
        ProviderAttemptEvent(
            request_id="req-1",
            timestamp=datetime.now(),
            event_type="provider_attempt",
            provider="openrouter",
            attempt=1,
        )
    )

    record_metric(
        ProviderSuccessEvent(
            request_id="req-1",
            timestamp=datetime.now(),
            event_type="provider_success",
            provider="openrouter",
            latency_ms=1500.0,
            input_tokens=15,
            output_tokens=45,
        )
    )

    record_metric(
        StreamFirstTokenEvent(
            request_id="req-1",
            timestamp=datetime.now(),
            event_type="stream_first_token",
            provider="openrouter",
            ttft_ms=250.0,
        )
    )

    exposition = prometheus_metrics.generate_exposition().decode("utf-8")

    assert "gateway_requests_total{status=\"started\",team_id=\"prom-team\"}" in exposition
    assert "gateway_provider_attempts_total{provider=\"openrouter\"}" in exposition
    assert "gateway_tokens_total{provider=\"openrouter\",type=\"input\"}" in exposition
    assert "gateway_tokens_total{provider=\"openrouter\",type=\"output\"}" in exposition
    assert "gateway_stream_ttft_seconds_bucket" in exposition


def test_metrics_endpoint_prometheus_and_json():
    """Test HTTP GET /metrics and GET /v1/metrics endpoints."""
    client = TestClient(app)

    # 1. Root /metrics (Prometheus text format)
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.headers["content-type"]
    assert "gateway_requests_total" in res.text

    # 2. /v1/metrics (Prometheus text format)
    res_v1 = client.get("/v1/metrics")
    assert res_v1.status_code == 200
    assert "text/plain" in res_v1.headers["content-type"]
    assert "gateway_requests_total" in res_v1.text

    # 3. Backwards compatible JSON format
    res_json = client.get("/v1/metrics?format=json")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]
    data = res_json.json()
    assert "total_requests" in data
