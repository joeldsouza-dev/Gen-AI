import pytest

from app.core.models import (
    GatewayRequest,
    ProviderName,
    RateLimitError,
    GatewayResponse,
)
from app.core.router import GatewayRouter



class RejectingRateLimiter:
    async def allow(self, tokens_requested: int = 1) -> bool:
        return False

    
class AllowingRateLimiter:
    async def allow(self, tokens_requested: int = 1) -> bool:
        return True


class FakeProvider:
    async def call(self, request: GatewayRequest):
        return GatewayResponse(
            text="Hello from Fake Provider!",
            provider_used=ProviderName.OLLAMA,
            model_used="fake-model",
            input_tokens=5,
            output_tokens=4,
            latency_ms=10.0,
        )
class OpenCircuitBreaker:
    def allow_request(self):
        return False


class ClosedCircuitBreaker:
    def allow_request(self):
        return True

def test_build_chain_uses_default_order_without_preference():
    default_chain = [
        ProviderName.NVIDIA_NIM,
        ProviderName.OPENROUTER,
        ProviderName.OLLAMA,
    ]

    router = GatewayRouter(
        providers={},
        circuit_breakers={},
        rate_limiter=None,
        default_chain=default_chain,
    )

    request = GatewayRequest(
        team_id="test-team",
        prompt="Hello",
    )

    chain = router._build_chain(request)

    assert chain == default_chain


def test_build_chain_puts_preferred_provider_first():
    default_chain = [
        ProviderName.NVIDIA_NIM,
        ProviderName.OPENROUTER,
        ProviderName.OLLAMA,
    ]

    router = GatewayRouter(
        providers={},
        circuit_breakers={},
        rate_limiter=None,
        default_chain=default_chain,
    )

    request = GatewayRequest(
        team_id="test-team",
        prompt="Hello",
        preferred_provider=ProviderName.OLLAMA,
    )

    chain = router._build_chain(request)

    assert chain == [
        ProviderName.OLLAMA,
        ProviderName.NVIDIA_NIM,
        ProviderName.OPENROUTER,
    ]


@pytest.mark.asyncio
async def test_route_request_rejects_rate_limited_request():
    router = GatewayRouter(
        providers={},
        circuit_breakers={},
        rate_limiter=RejectingRateLimiter(),
        default_chain=[],
    )

    request = GatewayRequest(
        team_id="test-team",
        prompt="Hello",
    )

    with pytest.raises(RateLimitError):
        await router.route_request(request)



@pytest.mark.asyncio
async def test_route_request_returns_provider_response():
    router = GatewayRouter(
        providers={
            ProviderName.OLLAMA: FakeProvider(),
        },
        circuit_breakers={},
        rate_limiter=AllowingRateLimiter(),
        default_chain=[
            ProviderName.OLLAMA,
        ],
    )

    request = GatewayRequest(
        team_id="test-team",
        prompt="Hello",
    )

    response = await router.route_request(request)

    assert response.text == "Hello from Fake Provider!"
    assert response.provider_used == ProviderName.OLLAMA

@pytest.mark.asyncio
async def test_route_request_skips_open_circuit_breaker():
    router = GatewayRouter(
        providers={
            ProviderName.OLLAMA: FakeProvider(),
        },
        circuit_breakers={
            ProviderName.OLLAMA: OpenCircuitBreaker(),
        },
        rate_limiter=AllowingRateLimiter(),
        default_chain=[
            ProviderName.OLLAMA,
        ],
    )

    request = GatewayRequest(
        team_id="test-team",
        prompt="Hello",
    )

    with pytest.raises(RuntimeError):
        await router.route_request(request)