from app.core.models import GatewayRequest, ProviderName
from app.core.router import GatewayRouter


def test_build_chain_uses_default_order_without_preference():
    default_chain = [
        ProviderName.NVIDIA_NIM,
        ProviderName.OPENROUTER,
        ProviderName.OLLAMA,
    ]

    router = GatewayRouter(
        providers={},
        circuit_breakers={},
        rate_limiter=None,
        default_chain=default_chain,
    )

    request = GatewayRequest(
        team_id="test-team",
        prompt="Hello",
    )

    chain = router._build_chain(request)

    assert chain == [
        ProviderName.NVIDIA_NIM,
        ProviderName.OPENROUTER,
        ProviderName.OLLAMA,
    ]
def test_build_chain_puts_preferred_provider_first():
    default_chain = [
        ProviderName.NVIDIA_NIM,
        ProviderName.OPENROUTER,
        ProviderName.OLLAMA,
    ]

    router = GatewayRouter(
        providers={},
        circuit_breakers={},
        rate_limiter=None,
        default_chain=default_chain,
    )

    request = GatewayRequest(
        team_id="test-team",
        prompt="Hello",
        preferred_provider=ProviderName.OLLAMA,
    )

    chain = router._build_chain(request)

    assert chain == [
        ProviderName.OLLAMA,
        ProviderName.NVIDIA_NIM,
        ProviderName.OPENROUTER,
    ]