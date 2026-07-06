"""
OpenRouter provider.

API reference: https://openrouter.ai/docs
Also an OpenAI-compatible /chat/completions endpoint, so the shape of your
implementation here should end up very close to NvidiaNimProvider — that
similarity is exactly why the BaseProvider abstraction works.

Auth: Bearer token in the Authorization header, e.g.
    Authorization: Bearer <OPENROUTER_API_KEY>

Endpoint: POST {OPENROUTER_BASE_URL}/chat/completions

Two things that differ from NIM and are worth handling deliberately:
  1. Free-tier models (IDs ending in `:free`) are rate-limited more
     aggressively by OpenRouter itself — you'll likely see 429s during
     testing. Make sure your retryable/non-retryable classification treats
     429 as retryable so the router's fallback logic actually gets exercised.
  2. OpenRouter recommends setting an `HTTP-Referer` and `X-Title` header —
     check current docs for whether this is still required/recommended and
     decide if you want to include it.

TODO(you): implement `call()` and `health_check()` following the same
structure as NvidiaNimProvider — build payload, time the request, translate
success/failure into GatewayResponse / ProviderError.
"""

import time

import httpx

from app.config import settings
from app.core.models import GatewayRequest, GatewayResponse, ProviderError, ProviderName
from app.providers.base import BaseProvider


class OpenRouterProvider(BaseProvider):
    name = ProviderName.OPENROUTER

    def __init__(self):
        self.base_url = settings.openrouter_base_url
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model

    async def call(self, request: GatewayRequest) -> GatewayResponse:
        # TODO(you): implement. See docstring above.
        raise NotImplementedError("Implement OpenRouterProvider.call()")

    async def health_check(self) -> bool:
        # TODO(you): implement.
        raise NotImplementedError("Implement OpenRouterProvider.health_check()")
