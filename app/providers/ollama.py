"""
Ollama provider — local, no API key, no rate limits, no cost.

Build this one FIRST (see README build order). It removes network cost/latency
variance from the picture while you get the plumbing (config, models, error
handling, latency measurement) working, and gives you a reliable local
fallback-of-last-resort once the other two providers are in.

API reference: https://github.com/ollama/ollama/blob/main/docs/api.md

Endpoint: POST {OLLAMA_BASE_URL}/api/chat
Body shape is different from OpenAI's — it's Ollama's own format, not
OpenAI-compatible (unlike NIM and OpenRouter). This is actually useful:
implementing this one forces you to prove your BaseProvider abstraction
is real and not just "copy the same OpenAI payload three times."

Notes:
  - No Authorization header needed for local Ollama.
  - Response is either a single JSON object (if you pass "stream": false)
    or newline-delimited JSON chunks (if streaming). Start with stream: false
    for simplicity — streaming can come later once the basic path works.
  - Make sure Ollama is running locally (`ollama serve`) and you've pulled
    a model (`ollama pull llama3.1`) before testing this.

TODO(you): implement `call()` and `health_check()`.
For health_check, GET {base_url}/api/tags is a good lightweight check —
it lists locally available models without running any inference.
"""

import time

import httpx

from app.config import settings
from app.core.models import GatewayRequest, GatewayResponse, ProviderError, ProviderName
from app.providers.base import BaseProvider


class OllamaProvider(BaseProvider):
    name = ProviderName.OLLAMA

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def call(self, request: GatewayRequest) -> GatewayResponse:
        messages=[]
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
        print(payload)
        start_time = time.perf_counter()
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload, timeout=30.0)

    
        latency_ms = (time.perf_counter() - start_time) * 1000

        response.raise_for_status()

        data = response.json()

        print("OLLAMA RESPONSE:")
        print(data)

        return GatewayResponse(
            text=data["message"]["content"],
            provider_used=self.name,
            model_used=data["model"],
            input_tokens=data["prompt_eval_count"],
            output_tokens=data["eval_count"],
            latency_ms=latency_ms,
        )

        # TODO(you): implement. See docstring above — note the different
            # request/response shape compared to NVIDIA NIM / OpenRouter.
    

    async def health_check(self) -> bool:
        # TODO(you): implement, e.g. GET {base_url}/api/tags
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
        raise NotImplementedError("Implement OllamaProvider.health_check()")
