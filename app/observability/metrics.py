from dataclasses import dataclass, field
from threading import Lock


@dataclass
class MetricsCollector:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    provider_attempts: dict[str, int] = field(default_factory=dict)
    provider_successes: dict[str, int] = field(default_factory=dict)
    provider_failures: dict[str, int] = field(default_factory=dict)
    provider_retries: dict[str, int] = field(default_factory=dict)
    provider_fallbacks: dict[str, int] = field(default_factory=dict)

    # Latency
    provider_latency_total_ms: dict[str, float] = field(default_factory=dict)
    provider_latency_count: dict[str, int] = field(default_factory=dict)
    provider_latency_min_ms: dict[str, float] = field(default_factory=dict)
    provider_latency_max_ms: dict[str, float] = field(default_factory=dict)

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0

    provider_input_tokens: dict[str, int] = field(default_factory=dict)
    provider_output_tokens: dict[str, int] = field(default_factory=dict)

    _lock: Lock = field(default_factory=Lock, repr=False)

    def increment_request(self) -> None:
        with self._lock:
            self.total_requests += 1

    def increment_success(self) -> None:
        with self._lock:
            self.successful_requests += 1

    def increment_failure(self) -> None:
        with self._lock:
            self.failed_requests += 1

    def increment_provider_attempt(self, provider: str) -> None:
        with self._lock:
            self.provider_attempts[provider] = (
                self.provider_attempts.get(provider, 0) + 1
            )

    def record_provider_success(
        self,
        provider: str,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        with self._lock:
            self.provider_successes[provider] = (
                self.provider_successes.get(provider, 0) + 1
            )

            # -----------------------------
            # Latency
            # -----------------------------

            self.provider_latency_total_ms[provider] = (
                self.provider_latency_total_ms.get(provider, 0.0)
                + latency_ms
            )

            self.provider_latency_count[provider] = (
                self.provider_latency_count.get(provider, 0)
                + 1
            )

            current_min = self.provider_latency_min_ms.get(provider)

            if current_min is None or latency_ms < current_min:
                self.provider_latency_min_ms[provider] = latency_ms

            current_max = self.provider_latency_max_ms.get(provider)

            if current_max is None or latency_ms > current_max:
                self.provider_latency_max_ms[provider] = latency_ms

            # -----------------------------
            # Tokens
            # -----------------------------

            self.input_tokens += input_tokens
            self.output_tokens += output_tokens

            self.provider_input_tokens[provider] = (
                self.provider_input_tokens.get(provider, 0)
                + input_tokens
            )

            self.provider_output_tokens[provider] = (
                self.provider_output_tokens.get(provider, 0)
                + output_tokens
            )

    def increment_provider_failure(self, provider: str) -> None:
        with self._lock:
            self.provider_failures[provider] = (
                self.provider_failures.get(provider, 0) + 1
            )

    def increment_provider_retry(self, provider: str) -> None:
        with self._lock:
            self.provider_retries[provider] = (
                self.provider_retries.get(provider, 0) + 1
            )

    def increment_provider_fallback(self, provider: str) -> None:
        with self._lock:
            self.provider_fallbacks[provider] = (
                self.provider_fallbacks.get(provider, 0) + 1
            )

    def snapshot(self) -> dict:
        with self._lock:

            latency = {}

            for provider, total in self.provider_latency_total_ms.items():
                count = self.provider_latency_count[provider]

                latency[provider] = {
                    "average_ms": total / count,
                    "min_ms": self.provider_latency_min_ms[provider],
                    "max_ms": self.provider_latency_max_ms[provider],
                }

            total_tokens = self.input_tokens + self.output_tokens

            return {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,

                "provider_attempts": dict(
                    self.provider_attempts
                ),

                "provider_successes": dict(
                    self.provider_successes
                ),

                "provider_failures": dict(
                    self.provider_failures
                ),

                "provider_retries": dict(
                    self.provider_retries
                ),

                "provider_fallbacks": dict(
                    self.provider_fallbacks
                ),

                "latency": latency,

                "tokens": {
                    "input": self.input_tokens,
                    "output": self.output_tokens,
                    "total": total_tokens,
                },

                "provider_tokens": {
                    provider: {
                        "input": self.provider_input_tokens.get(
                            provider, 0
                        ),
                        "output": self.provider_output_tokens.get(
                            provider, 0
                        ),
                        "total": (
                            self.provider_input_tokens.get(
                                provider, 0
                            )
                            + self.provider_output_tokens.get(
                                provider, 0
                            )
                        ),
                    }
                    for provider in set(
                        self.provider_input_tokens
                    )
                    | set(self.provider_output_tokens)
                },
            }