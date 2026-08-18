"""
The provider contract. READ THIS FILE FIRST before writing any provider.

Every provider (NVIDIA NIM, OpenRouter, Ollama) is a different HTTP API with
a different request/response shape. Your job in each provider file is to
translate GatewayRequest -> that provider's format, make the call, and
translate that provider's response -> GatewayResponse. If you get this
abstraction right, the router (app/core/router.py) never needs to know
which provider it's talking to.

Why this matters (this is the actual lesson of the project, not busywork):
a leaky abstraction here is exactly what makes multi-provider fallback
systems fragile in production. If NVIDIA NIM's error format leaks through
to your router's error-handling logic, your fallback logic now has to know
about NVIDIA NIM specifically, and adding a 4th provider means touching
code all over the codebase instead of just adding one new file.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator

from app.core.models import GatewayRequest, GatewayResponse, StreamChunk


class BaseProvider(ABC):
    name: str  # set in each subclass, must match a ProviderName value

    @abstractmethod
    async def call(self, request: GatewayRequest) -> GatewayResponse:
        """
        Make the actual API call to this provider and return a GatewayResponse.

        Must raise `app.core.models.ProviderError` on failure — set
        `retryable=True` for things like timeouts/5xx/rate-limits, and
        `retryable=False` for things like auth failures or invalid requests
        (retrying those wastes time and just delays the fallback).

        Must measure and include real latency_ms — don't hardcode it.
        """
        raise NotImplementedError

    @abstractmethod
    async def call_stream(self, request: GatewayRequest) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream token chunks from this provider, yielding StreamChunk objects.
        Must raise `ProviderError` if initial connection fails before emitting chunks.
        """
        raise NotImplementedError
        yield  # Make it a generator syntax

    @abstractmethod
    async def health_check(self) -> bool:
        """
        A cheap, fast call used by the circuit breaker's half-open state to
        test whether a previously-failing provider has recovered.
        """
        raise NotImplementedError
