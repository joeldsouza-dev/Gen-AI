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
from app.core.models import GatewayRequest, GatewayResponse, ProviderError, ProviderName, StreamChunk
from app.providers.base import BaseProvider


class NvidiaNimProvider(BaseProvider):
    name = ProviderName.NVIDIA_NIM

    def __init__(self):
        self.base_url = settings.nvidia_nim_base_url
        self.api_key = settings.nvidia_nim_api_key
        self.model = settings.nvidia_nim_model

    async def call(self, request: GatewayRequest) -> GatewayResponse:
            messages = []
    
            if request.system_prompt:
                messages.append(
                    {
                        "role": "system",
                        "content": request.system_prompt,
                    }
                )
    
            messages.append(
                {
                    "role": "user",
                    "content": request.prompt,
                }
            )
    
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }

            headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"     # Optional but recommended
        }
    
            start_time = time.perf_counter()
    
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=60.0,  # Use default timeout
                    )
    
                response.raise_for_status()
    
            except httpx.TimeoutException as exc:
                raise ProviderError(
                    f"Error calling nvidia_nim  API: {exc}",
                    retryable=True,
                ) from exc
    
            except httpx.HTTPStatusError as exc:
                print("=" * 80)
                print("NVIDIA NIM HTTP ERROR")
                print("Status :", exc.response.status_code)
                print("Body   :", exc.response.text)
                print("=" * 80)
    
                raise ProviderError(
                    f"NVIDIA NIM returned HTTP {exc.response.status_code}: {exc.response.text}",
                    retryable=exc.response.status_code == 429 or exc.response.status_code >= 500,
                ) from exc
    
            except httpx.RequestError as exc:
                print("=" * 80)
                print("NVIDIA NIM REQUEST ERROR")
                print(repr(exc))
                print("=" * 80)
    
                raise ProviderError(
                    f"Error calling NVIDIA NIM API: {exc}",
                    retryable=True,
                ) from exc
    
            latency_ms = (time.perf_counter() - start_time) * 1000
    
            data = response.json()
    
            try:
                return GatewayResponse(
                    text=data["choices"][0]["message"]["content"],
                    provider_used=self.name,
                    model_used=data["model"],
                    input_tokens=data["usage"]["prompt_tokens"],
                    output_tokens=data["usage"]["completion_tokens"],
                    latency_ms=latency_ms,
                )
    
            except (KeyError, ValueError) as exc:
                raise ProviderError(
                    f"Unexpected response format from NVIDIA NIM API: {data}",
                    retryable=False,
                ) from exc

    async def call_stream(self, request: GatewayRequest):
        import json
        messages = []

        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})

        messages.append({"role": "user", "content": request.prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            client = httpx.AsyncClient()
            req = client.build_request("POST", f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=60.0)
            response = await client.send(req, stream=True)

            if response.status_code >= 400:
                body = await response.aread()
                await response.aclose()
                await client.aclose()
                raise ProviderError(
                    f"NVIDIA NIM returned HTTP {response.status_code}: {body.decode()}",
                    retryable=response.status_code == 429 or response.status_code >= 500,
                )

            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    choices = data.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        finish_reason = choices[0].get("finish_reason")
                        if content or finish_reason:
                            yield StreamChunk(
                                text=content,
                                provider_used=self.name,
                                model_used=data.get("model", self.model),
                                is_final=finish_reason is not None,
                                finish_reason=finish_reason,
                            )
                except Exception:
                    continue

            await response.aclose()
            await client.aclose()

        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise ProviderError(f"Error streaming from NVIDIA NIM API: {exc}", retryable=True) from exc
    
    async def health_check(self) -> bool:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-OpenRouter-Title": "LLM Gateway",
            }
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/models",
                        headers=headers,
                        timeout=5.0,
                    )
                if response.status_code >= 400:
                    print("=" * 80)
                    print("NVIDIA NIM ERROR")
                    print("Status:", response.status_code)
                    print("Response:", response.text)
                    print("=" * 80)
    
                response.raise_for_status()

                data = response.json()

                print("=" * 80)
                print("Parsed JSON:")
                print(data)
                print("=" * 80)

                return any(
                    model["id"] == self.model
                    for model in data["data"]
                )
    
            except httpx.HTTPError:
                return False