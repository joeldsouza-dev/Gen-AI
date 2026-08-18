import json
import time

import httpx

from app.config import settings
from app.core.models import (
    GatewayRequest,
    GatewayResponse,
    ProviderError,
    ProviderName,
    StreamChunk,
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

    async def call_stream(self, request: GatewayRequest):
        messages = []

        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})

        messages.append({"role": "user", "content": request.prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        client = httpx.AsyncClient()
        try:
            req = client.build_request("POST", f"{self.base_url}/api/chat", json=payload, timeout=60.0)
            response = await client.send(req, stream=True)

            if response.status_code >= 400:
                body = await response.aread()
                await response.aclose()
                raise ProviderError(
                    f"Ollama returned HTTP {response.status_code}: {body.decode()}",
                    retryable=response.status_code >= 500,
                )

            try:
                async for line in response.aiter_lines():
                    if not line or not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        text_delta = data.get("message", {}).get("content", "")
                        is_final = data.get("done", False)
                        yield StreamChunk(
                            text=text_delta,
                            provider_used=self.name,
                            model_used=data.get("model", self.model),
                            is_final=is_final,
                        )
                    except Exception:
                        continue
            finally:
                await response.aclose()

        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise ProviderError(f"Error streaming from Ollama API: {exc}", retryable=True) from exc
        finally:
            await client.aclose()

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