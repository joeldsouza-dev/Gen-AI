import asyncio

from app.core.models import GatewayRequest
from app.providers.openrouter import OpenRouterProvider


async def main():
    provider = OpenRouterProvider()

    print("Running health check...")
    healthy = await provider.health_check()
    print(f"Healthy: {healthy}")

    request = GatewayRequest(
        team_id="test-team",
        prompt="Explain what an LLM Gateway is in two sentences.",
        system_prompt="You are a helpful assistant.",
        preferred_provider=None,
    )

    response = await provider.call(request)

    print("\n===== RESPONSE =====")
    print(response)


if __name__ == "__main__":
    provider = OpenRouterProvider()
    print(provider.base_url)
    asyncio.run(main())