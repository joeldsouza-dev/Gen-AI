from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


class PrometheusCollector:
    """Production-grade Prometheus metrics registry for the LLM Gateway."""

    def __init__(self, registry: CollectorRegistry = None):
        self.registry = registry or CollectorRegistry()

        # 1. Total Requests Counter (labels: status [success|failed], team_id)
        self.requests_total = Counter(
            "gateway_requests_total",
            "Total HTTP requests handled by the LLM gateway (by final status).",
            ["status", "team_id"],
            registry=self.registry,
        )

        # 1b. In-Flight Requests Gauge (labels: team_id)
        self.requests_in_flight = Gauge(
            "gateway_requests_in_flight",
            "Current number of in-flight HTTP requests.",
            ["team_id"],
            registry=self.registry,
        )

        # 2. Provider Attempts Counter (labels: provider)
        self.provider_attempts_total = Counter(
            "gateway_provider_attempts_total",
            "Total request attempts made to each LLM provider.",
            ["provider"],
            registry=self.registry,
        )

        # 3. Provider Failures Counter (labels: provider)
        self.provider_failures_total = Counter(
            "gateway_provider_failures_total",
            "Total failure count encountered per provider.",
            ["provider"],
            registry=self.registry,
        )

        # 4. Fallbacks Counter (labels: from_provider, to_provider)
        self.fallbacks_total = Counter(
            "gateway_fallbacks_total",
            "Total provider failover events.",
            ["from_provider", "to_provider"],
            registry=self.registry,
        )

        # 5. Tokens Counter (labels: provider, type)
        self.tokens_total = Counter(
            "gateway_tokens_total",
            "Cumulative token usage per provider (input/output).",
            ["provider", "type"],
            registry=self.registry,
        )

        # 6. Circuit Breaker State Gauge (labels: provider)
        # 0 = CLOSED, 1 = OPEN, 0.5 = HALF_OPEN
        self.circuit_breaker_state = Gauge(
            "gateway_circuit_breaker_state",
            "Current gauge state of provider circuit breaker (0=CLOSED, 1=OPEN, 0.5=HALF_OPEN).",
            ["provider"],
            registry=self.registry,
        )

        # 7. TTFT Histogram (labels: provider)
        self.stream_ttft_seconds = Histogram(
            "gateway_stream_ttft_seconds",
            "Time To First Token (TTFT) latency in seconds.",
            ["provider"],
            buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry,
        )

        # 8. Stream & Request Duration Histogram (labels: provider)
        self.stream_duration_seconds = Histogram(
            "gateway_stream_duration_seconds",
            "Total request/stream latency duration in seconds.",
            ["provider"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry,
        )

    def generate_exposition(self) -> bytes:
        """Generate Prometheus exposition text format (version=0.0.4)."""
        return generate_latest(self.registry)


prometheus_metrics = PrometheusCollector()
