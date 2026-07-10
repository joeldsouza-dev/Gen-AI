"""
Test ONE provider directly — no FastAPI, no rate limiter, no circuit breaker.
Run with: python scripts/test_provider_direct.py
Prerequisites: `ollama serve` running, `ollama pull llama3.1` done.
"""

import asyncio
from app.core.models import GatewayRequest
from app.providers.ollama import OllamaProvider


async def main():
    provider = OllamaProvider()

    print(f"Checking health of {provider.name} at {provider.base_url} ...")
    healthy = await provider.health_check()
    print(f"  health_check() -> {healthy}")
    if not healthy:
        print("  Ollama doesn't seem to be reachable. Is `ollama serve` running?")
        return

    request = GatewayRequest(team_id="local-test", prompt="Say hello in exactly one short sentence.")

    print(f"\nSending request to {provider.name} (model: {provider.model}) ...")
    try:
        response = await provider.call(request)
    except Exception as e:
        print(f"  call() raised: {e!r}")
        return

    print("  Success:")
    print(f"    text:          {response.text!r}")
    print(f"    provider_used: {response.provider_used}")
    print(f"    model_used:    {response.model_used}")
    print(f"    input_tokens:  {response.input_tokens}")
    print(f"    output_tokens: {response.output_tokens}")
    print(f"    latency_ms:    {response.latency_ms:.1f}")


if __name__ == "__main__":
    asyncio.run(main())