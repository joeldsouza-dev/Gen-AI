"""
Standardized request/response models used across all providers.

This is done for you. The whole point of the Gateway is that a caller
sends a `GatewayRequest` and gets back a `GatewayResponse` without needing
to know or care whether NVIDIA NIM, OpenRouter, or Ollama actually served it.
Each provider module is responsible for translating ITS OWN request/response
format to/from these shared models — that translation is where you'll write
real code (see app/providers/base.py).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProviderName(str, Enum):
    NVIDIA_NIM = "nvidia_nim"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"


class GatewayRequest(BaseModel):
    """What a caller sends to the gateway. Deliberately provider-agnostic."""

    team_id: str = Field(..., description="Which team is making this request — used for rate limiting/budgets.")
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: int = 512
    temperature: float = 0.7
    # Which provider tier to prefer. The router decides the actual fallback chain —
    # this is a *hint*, not a guarantee, since the whole point is automatic failover.
    preferred_provider: Optional[ProviderName] = None


class GatewayResponse(BaseModel):
    """What the gateway returns, regardless of which provider actually served it."""

    text: str
    provider_used: ProviderName
    model_used: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    # True if the preferred/primary provider failed and this came from a fallback.
    was_fallback: bool = False


class ProviderError(Exception):
    """Raised by a provider implementation when the call fails.

    Distinguish retryable vs non-retryable in your provider code by raising
    this with `retryable=True/False` — the router needs that distinction to
    decide whether to retry the same provider or move straight to fallback.
    """
class RateLimitError(Exception):
    """Raised when a request exceeds the configured rate limit."""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable
