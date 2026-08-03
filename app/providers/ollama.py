import time

import httpx

from app.config import settings
from app.core.models import (
    GatewayRequest,
    GatewayResponse,
    ProviderError,
    ProviderName,
)
from app.providers.base import BaseProvider


class OllamaProvider(BaseProvider):
    name = ProviderName.OLLAMA

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

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
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=None,  # Use default timeout
                )

            response.raise_for_status()

        except httpx.TimeoutException as exc:
            raise ProviderError(
                f"Error calling Ollama API: {exc}",
                retryable=True,
            ) from exc

        except httpx.HTTPStatusError as exc:
            print("=" * 80)
            print("OLLAMA HTTP ERROR")
            print("Status :", exc.response.status_code)
            print("Body   :", exc.response.text)
            print("=" * 80)

            raise ProviderError(
                f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text}",
                retryable=exc.response.status_code >= 500,
            ) from exc

        except httpx.RequestError as exc:
            print("=" * 80)
            print("REQUEST ERROR")
            print(repr(exc))
            print("=" * 80)

            raise ProviderError(
                f"Error calling Ollama API: {exc}",
                retryable=True,
            ) from exc

        latency_ms = (time.perf_counter() - start_time) * 1000

        data = response.json()

        try:
            return GatewayResponse(
                text=data["message"]["content"],
                provider_used=self.name,
                model_used=data["model"],
                input_tokens=data["prompt_eval_count"],
                output_tokens=data["eval_count"],
                latency_ms=latency_ms,
            )

        except (KeyError, ValueError) as exc:
            raise ProviderError(
                f"Unexpected response format from Ollama API: {data}",
                retryable=False,
            ) from exc

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0,
                )
            if response.status_code >= 400:
                print("=" * 80)
                print("OLLAMA ERROR")
                print("Status:", response.status_code)
                print("Response:", response.text)
                print("=" * 80)

            response.raise_for_status()
            print("=" * 80)
            print("Parsed JSON:")
            print(response.json())
            print("=" * 80)
            return True

        except httpx.HTTPError:
            return False