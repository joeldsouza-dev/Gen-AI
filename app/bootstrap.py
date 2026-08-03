from app.core.circuit_breaker import CircuitBreaker
from app.core.models import ProviderName
from app.core.rate_limiter import InMemoryTokenBucket
from app.core.router import GatewayRouter
from app.providers.ollama import OllamaProvider
from app.providers.openrouter import OpenRouterProvider


def create_providers():
    """
    Create and register all available LLM providers.
    """
    return {
        ProviderName.OLLAMA: OllamaProvider(),
        ProviderName.OPENROUTER: OpenRouterProvider(),
    }


def create_circuit_breakers():
    """
    Create one circuit breaker per provider.
    """
    return {
            ProviderName.OLLAMA: CircuitBreaker(
            failure_threshold=3,
            cooldown_seconds=30,
        ),
        ProviderName.OPENROUTER: CircuitBreaker(
            failure_threshold=3,
            cooldown_seconds=30,
        ),
    }


def create_rate_limiter():
    """
    Create the application's shared rate limiter.
    """
    return InMemoryTokenBucket(
        capacity=60,
        refill_rate_per_second=1,
    )


def create_gateway_router():
    """
    Compose the GatewayRouter with all of its dependencies.
    """
    providers = create_providers()
    circuit_breakers = create_circuit_breakers()
    rate_limiter = create_rate_limiter()

    return GatewayRouter(
        providers=providers,
        circuit_breakers=circuit_breakers,
        rate_limiter=rate_limiter,
        default_chain=[
            ProviderName.OLLAMA,
            ProviderName.OPENROUTER
        ],
        max_retries=2,
    )