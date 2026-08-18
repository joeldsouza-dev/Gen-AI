import asyncio
import json
import pytest

from app.core.models import (
    GatewayRequest,
    ProviderError,
    ProviderName,
    RateLimitError,
    StreamChunk,
)
from app.core.router import GatewayRouter


class AllowingRateLimiter:
    async def allow(self, team_id: str = "default", tokens_requested: int = 1) -> bool:
        return True


class RejectingRateLimiter:
    async def allow(self, team_id: str = "default", tokens_requested: int = 1) -> bool:
        return False


class SpyCircuitBreaker:
    def __init__(self, allow=True):
        self.allow = allow
        self.success_called = False
        self.failure_called = False

    def allow_request(self):
        return self.allow

    def record_success(self):
        self.success_called = True

    def record_failure(self):
        self.failure_called = True


class FakeStreamProvider:
    name = ProviderName.OLLAMA

    async def call(self, request: GatewayRequest):
        raise NotImplementedError

    async def call_stream(self, request: GatewayRequest):
        yield StreamChunk(
            text="Hello",
            provider_used=self.name,
            model_used="fake-model",
        )
        yield StreamChunk(
            text=" world!",
            provider_used=self.name,
            model_used="fake-model",
            is_final=True,
        )

    async def health_check(self) -> bool:
        return True


class FailingStreamProvider:
    name = ProviderName.OLLAMA

    async def call(self, request: GatewayRequest):
        raise NotImplementedError

    async def call_stream(self, request: GatewayRequest):
        raise ProviderError("Connection failed before first chunk", retryable=True)
        yield  # Make generator

    async def health_check(self) -> bool:
        return False


class FallbackStreamProvider:
    name = ProviderName.NVIDIA_NIM

    async def call(self, request: GatewayRequest):
        raise NotImplementedError

    async def call_stream(self, request: GatewayRequest):
        yield StreamChunk(
            text="Fallback chunk",
            provider_used=self.name,
            model_used="nvidia-model",
            is_final=True,
        )

    async def health_check(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_route_stream_yields_sse_formatted_chunks():
    router = GatewayRouter(
        providers={
            ProviderName.OLLAMA: FakeStreamProvider(),
        },
        circuit_breakers={
            ProviderName.OLLAMA: SpyCircuitBreaker(),
        },
        rate_limiter=AllowingRateLimiter(),
        default_chain=[ProviderName.OLLAMA],
    )

    request = GatewayRequest(team_id="team-1", prompt="Hello", stream=True)

    chunks = []
    async for chunk in router.route_stream(request):
        chunks.append(chunk)

    assert len(chunks) == 3
    assert chunks[0].startswith("data: ")
    assert "Hello" in chunks[0]
    assert "world!" in chunks[1]
    assert chunks[2] == "data: [DONE]\n\n"


@pytest.mark.asyncio
async def test_route_stream_pre_first_chunk_fallback():
    ollama_breaker = SpyCircuitBreaker()
    nvidia_breaker = SpyCircuitBreaker()

    router = GatewayRouter(
        providers={
            ProviderName.OLLAMA: FailingStreamProvider(),
            ProviderName.NVIDIA_NIM: FallbackStreamProvider(),
        },
        circuit_breakers={
            ProviderName.OLLAMA: ollama_breaker,
            ProviderName.NVIDIA_NIM: nvidia_breaker,
        },
        rate_limiter=AllowingRateLimiter(),
        default_chain=[ProviderName.OLLAMA, ProviderName.NVIDIA_NIM],
    )

    request = GatewayRequest(team_id="team-1", prompt="Hello", stream=True)

    chunks = []
    async for chunk in router.route_stream(request):
        chunks.append(chunk)

    assert len(chunks) == 2
    assert "Fallback chunk" in chunks[0]
    assert chunks[1] == "data: [DONE]\n\n"

    assert ollama_breaker.failure_called is True
    assert nvidia_breaker.success_called is True


@pytest.mark.asyncio
async def test_route_stream_rate_limit_rejection():
    router = GatewayRouter(
        providers={},
        circuit_breakers={},
        rate_limiter=RejectingRateLimiter(),
        default_chain=[],
    )

    request = GatewayRequest(team_id="team-1", prompt="Hello", stream=True)

    with pytest.raises(RateLimitError):
        async for _ in router.route_stream(request):
            pass
