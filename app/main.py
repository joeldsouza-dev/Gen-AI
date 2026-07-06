"""
App entrypoint. This wires the concrete providers/limiters/breakers into a
GatewayRouter and attaches it to the API layer.

This file is mostly done for you, but you'll need to come back and adjust
the construction calls (e.g. what args InMemoryTokenBucket / CircuitBreaker
take) once you've finalized their real constructors while implementing them.
Treat this as "the wiring will need small tweaks as your implementations
solidify" rather than "this is finished and won't change."
"""

from fastapi import FastAPI

from app.api import routes
from app.config import settings
from app.core.circuit_breaker import CircuitBreaker
from app.core.models import ProviderName
from app.core.rate_limiter import InMemoryTokenBucket
from app.core.router import GatewayRouter
from app.providers.nvidia_nim import NvidiaNimProvider
from app.providers.ollama import OllamaProvider
from app.providers.openrouter import OpenRouterProvider

app = FastAPI(title="LLM Gateway")
app.include_router(routes.router)


@app.on_event("startup")
async def startup() -> None:
    providers = {
        ProviderName.NVIDIA_NIM: NvidiaNimProvider(),
        ProviderName.OPENROUTER: OpenRouterProvider(),
        ProviderName.OLLAMA: OllamaProvider(),
    }

    circuit_breakers = {
        name: CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            cooldown_seconds=settings.circuit_breaker_cooldown_seconds,
        )
        for name in providers
    }

    # NOTE: a single shared bucket per process is a placeholder. Once you
    # implement per-team rate limiting, this likely becomes a dict of
    # buckets keyed by team_id (or a Redis-backed limiter keyed the same
    # way) — see rate_limiter.py.
    rate_limiter = InMemoryTokenBucket(
        capacity=settings.default_requests_per_minute,
        refill_rate_per_second=settings.default_requests_per_minute / 60,
    )

    routes.gateway_router = GatewayRouter(
        providers=providers,
        circuit_breakers=circuit_breakers,
        rate_limiter=rate_limiter,
        default_chain=[ProviderName.NVIDIA_NIM, ProviderName.OPENROUTER, ProviderName.OLLAMA],
    )
