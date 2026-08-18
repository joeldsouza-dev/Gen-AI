import pytest

from app.core.circuit_breaker import CircuitBreaker, CircuitState
from app.core.models import (
    GatewayRequest,
    GatewayResponse,
    ProviderError,
    ProviderName,
)
from app.core.router import GatewayRouter


class AllowingRateLimiter:
    async def allow(self, team_id: str = "default", tokens_requested: int = 1) -> bool:
        return True


class SuccessfulProvider:
    def __init__(self, name: ProviderName):
        self.name = name
        self.calls = 0

    async def call(self, request: GatewayRequest) -> GatewayResponse:
        self.calls += 1
        return GatewayResponse(
            text=f"Response from {self.name.value}",
            provider_used=self.name,
            model_used="test-model",
            input_tokens=10,
            output_tokens=20,
            latency_ms=15.0,
        )


class FailingProvider:
    def __init__(self, name: ProviderName, retryable: bool = False):
        self.name = name
        self.calls = 0
        self.retryable = retryable

    async def call(self, request: GatewayRequest) -> GatewayResponse:
        self.calls += 1
        raise ProviderError(
            message=f"{self.name.value} connection failed",
            retryable=self.retryable,
        )


@pytest.mark.asyncio
async def test_chain_test_a_nvidia_available():
    """Test A: NVIDIA available -> NVIDIA handles request."""
    nvidia = SuccessfulProvider(ProviderName.NVIDIA_NIM)
    openrouter = SuccessfulProvider(ProviderName.OPENROUTER)
    ollama = SuccessfulProvider(ProviderName.OLLAMA)

    router = GatewayRouter(
        providers={
            ProviderName.NVIDIA_NIM: nvidia,
            ProviderName.OPENROUTER: openrouter,
            ProviderName.OLLAMA: ollama,
        },
        circuit_breakers={
            ProviderName.NVIDIA_NIM: CircuitBreaker(failure_threshold=3, cooldown_seconds=30),
            ProviderName.OPENROUTER: CircuitBreaker(failure_threshold=3, cooldown_seconds=30),
            ProviderName.OLLAMA: CircuitBreaker(failure_threshold=3, cooldown_seconds=30),
        },
        rate_limiter=AllowingRateLimiter(),
        default_chain=[
            ProviderName.NVIDIA_NIM,
            ProviderName.OPENROUTER,
            ProviderName.OLLAMA,
        ],
        max_retries=0,
    )

    request = GatewayRequest(team_id="test-team", prompt="Test prompt")
    response = await router.route_request(request)

    assert response.provider_used == ProviderName.NVIDIA_NIM
    assert response.was_fallback is False
    assert nvidia.calls == 1
    assert openrouter.calls == 0
    assert ollama.calls == 0


@pytest.mark.asyncio
async def test_chain_test_b_nvidia_unavailable_fallback_to_openrouter():
    """Test B: NVIDIA unavailable -> OpenRouter handles request."""
    nvidia = FailingProvider(ProviderName.NVIDIA_NIM, retryable=False)
    openrouter = SuccessfulProvider(ProviderName.OPENROUTER)
    ollama = SuccessfulProvider(ProviderName.OLLAMA)

    router = GatewayRouter(
        providers={
            ProviderName.NVIDIA_NIM: nvidia,
            ProviderName.OPENROUTER: openrouter,
            ProviderName.OLLAMA: ollama,
        },
        circuit_breakers={
            ProviderName.NVIDIA_NIM: CircuitBreaker(failure_threshold=3, cooldown_seconds=30),
            ProviderName.OPENROUTER: CircuitBreaker(failure_threshold=3, cooldown_seconds=30),
            ProviderName.OLLAMA: CircuitBreaker(failure_threshold=3, cooldown_seconds=30),
        },
        rate_limiter=AllowingRateLimiter(),
        default_chain=[
            ProviderName.NVIDIA_NIM,
            ProviderName.OPENROUTER,
            ProviderName.OLLAMA,
        ],
        max_retries=0,
    )

    request = GatewayRequest(team_id="test-team", prompt="Test prompt")
    response = await router.route_request(request)

    assert response.provider_used == ProviderName.OPENROUTER
    assert response.was_fallback is True
    assert nvidia.calls == 1
    assert openrouter.calls == 1
    assert ollama.calls == 0


@pytest.mark.asyncio
async def test_chain_test_c_nvidia_and_openrouter_unavailable_fallback_to_ollama():
    """Test C: NVIDIA & OpenRouter unavailable -> Ollama handles request."""
    nvidia = FailingProvider(ProviderName.NVIDIA_NIM, retryable=False)
    openrouter = FailingProvider(ProviderName.OPENROUTER, retryable=False)
    ollama = SuccessfulProvider(ProviderName.OLLAMA)

    router = GatewayRouter(
        providers={
            ProviderName.NVIDIA_NIM: nvidia,
            ProviderName.OPENROUTER: openrouter,
            ProviderName.OLLAMA: ollama,
        },
        circuit_breakers={
            ProviderName.NVIDIA_NIM: CircuitBreaker(failure_threshold=3, cooldown_seconds=30),
            ProviderName.OPENROUTER: CircuitBreaker(failure_threshold=3, cooldown_seconds=30),
            ProviderName.OLLAMA: CircuitBreaker(failure_threshold=3, cooldown_seconds=30),
        },
        rate_limiter=AllowingRateLimiter(),
        default_chain=[
            ProviderName.NVIDIA_NIM,
            ProviderName.OPENROUTER,
            ProviderName.OLLAMA,
        ],
        max_retries=0,
    )

    request = GatewayRequest(team_id="test-team", prompt="Test prompt")
    response = await router.route_request(request)

    assert response.provider_used == ProviderName.OLLAMA
    assert response.was_fallback is True
    assert nvidia.calls == 1
    assert openrouter.calls == 1
    assert ollama.calls == 1


@pytest.mark.asyncio
async def test_chain_circuit_breaker_skips_open_provider():
    """Verify that an already OPEN circuit breaker skips NVIDIA without attempting it."""
    nvidia = FailingProvider(ProviderName.NVIDIA_NIM, retryable=False)
    openrouter = SuccessfulProvider(ProviderName.OPENROUTER)
    ollama = SuccessfulProvider(ProviderName.OLLAMA)

    nvidia_breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=30)
    nvidia_breaker.record_failure()
    assert nvidia_breaker.state == CircuitState.OPEN

    router = GatewayRouter(
        providers={
            ProviderName.NVIDIA_NIM: nvidia,
            ProviderName.OPENROUTER: openrouter,
            ProviderName.OLLAMA: ollama,
        },
        circuit_breakers={
            ProviderName.NVIDIA_NIM: nvidia_breaker,
            ProviderName.OPENROUTER: CircuitBreaker(failure_threshold=3, cooldown_seconds=30),
            ProviderName.OLLAMA: CircuitBreaker(failure_threshold=3, cooldown_seconds=30),
        },
        rate_limiter=AllowingRateLimiter(),
        default_chain=[
            ProviderName.NVIDIA_NIM,
            ProviderName.OPENROUTER,
            ProviderName.OLLAMA,
        ],
        max_retries=0,
    )

    request = GatewayRequest(team_id="test-team", prompt="Test prompt")
    response = await router.route_request(request)

    assert nvidia.calls == 0
    assert openrouter.calls == 1
    assert response.provider_used == ProviderName.OPENROUTER
    assert response.was_fallback is True
