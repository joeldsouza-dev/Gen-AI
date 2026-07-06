"""
NVIDIA NIM provider.

API reference: https://docs.api.nvidia.com/nim/reference
NIM exposes an OpenAI-compatible /chat/completions endpoint, so the request/
response shape is very close to what you'd send to OpenAI directly.

Auth: Bearer token in the Authorization header, e.g.
    Authorization: Bearer <NVIDIA_NIM_API_KEY>

Endpoint: POST {NVIDIA_NIM_BASE_URL}/chat/completions

TODO(you): implement `call()` and `health_check()`. Suggested steps for `call`:
  1. Build the OpenAI-style payload: model, messages (system + user), max_tokens, temperature.
  2. Record start time, make the httpx POST call, record end time -> latency_ms.
  3. On non-2xx response: raise ProviderError. Look at the status code to decide
     retryable (429, 500-599, timeouts) vs not (400, 401, 403).
  4. On success: parse the response JSON, pull out the text and token usage,
     and construct a GatewayResponse.
  5. Wrap the whole thing in a try/except for httpx.TimeoutException /
     httpx.ConnectError and re-raise as a retryable ProviderError — network-level
     failures should look the same to the router as HTTP-level failures.

For `health_check`, consider hitting GET {base_url}/models with a short timeout,
or sending a 1-token completion request — compare cost/speed of each approach
and pick one, and write down why in your ADR log.
"""

import time

import httpx

from app.config import settings
from app.core.models import GatewayRequest, GatewayResponse, ProviderError, ProviderName
from app.providers.base import BaseProvider


class NvidiaNimProvider(BaseProvider):
    name = ProviderName.NVIDIA_NIM

    def __init__(self):
        self.base_url = settings.nvidia_nim_base_url
        self.api_key = settings.nvidia_nim_api_key
        self.model = settings.nvidia_nim_model

    async def call(self, request: GatewayRequest) -> GatewayResponse:
        # TODO(you): implement. See docstring above for the steps.
        raise NotImplementedError("Implement NvidiaNimProvider.call()")

    async def health_check(self) -> bool:
        # TODO(you): implement a cheap liveness check.
        raise NotImplementedError("Implement NvidiaNimProvider.health_check()")
