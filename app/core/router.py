"""
The router — where everything else in this project gets wired together.

Responsibilities of route_request():

1. Check the rate limiter.
2. Build the provider fallback chain.
3. Check each provider's circuit breaker.
4. Attempt the provider.
5. Retry retryable failures.
6. Fall back to the next provider.
7. Emit observability events throughout the process.
8. Return a GatewayResponse on success.
9. Raise a clear error if every provider fails.
"""

import asyncio
from datetime import datetime
from typing import Dict, List

from app.core.circuit_breaker import CircuitBreaker
from app.core.models import (
    GatewayRequest,
    GatewayResponse,
    ProviderError,
    ProviderName,
    RateLimitError,
)
from app.observability import event_emitter
from app.observability.events import (
    FallbackEvent,
    ProviderAttemptEvent,
    ProviderFailureEvent,
    ProviderSuccessEvent,
    RetryEvent,
)
from app.providers.base import BaseProvider


class GatewayRouter:
    def __init__(
        self,
        providers: Dict[ProviderName, BaseProvider],
        circuit_breakers: Dict[ProviderName, CircuitBreaker],
        rate_limiter,
        default_chain: List[ProviderName],
        max_retries: int = 2,
    ):
        self.providers = providers
        self.circuit_breakers = circuit_breakers
        self.rate_limiter = rate_limiter
        self.max_retries = max_retries
        self.default_chain = default_chain

    async def route_request(
        self,
        request: GatewayRequest,
        request_id: str,
    ) -> GatewayResponse:

        # --------------------------------------------------
        # 1. Rate limit check
        # --------------------------------------------------

        allowed = await self.rate_limiter.allow()

        if not allowed:
            raise RateLimitError(
                f"Rate limit exceeded for team {request.team_id}",
                retryable=False,
            )

        # --------------------------------------------------
        # 2. Build provider chain
        # --------------------------------------------------

        provider_chain = self._build_chain(request)

        # --------------------------------------------------
        # 3. Try providers in order
        # --------------------------------------------------

        for index, provider_name in enumerate(provider_chain):

            breaker = self.circuit_breakers[provider_name]

            # --------------------------------------------------
            # 3a. Check circuit breaker
            # --------------------------------------------------

            if not breaker.allow_request():
                continue

            provider = self.providers[provider_name]

            # Initial attempt + configured retries
            total_attempts = 1 + self.max_retries

            # --------------------------------------------------
            # 3b. Attempt provider
            # --------------------------------------------------

            for attempt in range(total_attempts):

                # --------------------------------------------------
                # Emit provider attempt event
                # --------------------------------------------------

                event_emitter.emit(
                    ProviderAttemptEvent(
                        request_id=request_id,
                        timestamp=datetime.now(),
                        event_type="provider_attempt",
                        provider=provider_name.value,
                        attempt=attempt + 1,
                    )
                )

                try:
                    # --------------------------------------------------
                    # Call provider
                    # --------------------------------------------------

                    response = await provider.call(request)

                    # --------------------------------------------------
                    # Provider succeeded
                    # --------------------------------------------------

                    breaker.record_success()

                    event_emitter.emit(
                        ProviderSuccessEvent(
                           request_id=request_id,
                           timestamp=datetime.now(),
                           event_type="provider_success",
                           provider=provider_name.value,
                           latency_ms=response.latency_ms,
                           input_tokens=response.input_tokens,
                           output_tokens=response.output_tokens,
                        )
                     )

                    # Mark response as fallback if this wasn't
                    # the first provider in the chain.
                    response.was_fallback = index > 0

                    return response

                except ProviderError as error:

                    # --------------------------------------------------
                    # Provider failed
                    # --------------------------------------------------

                    event_emitter.emit(
                        ProviderFailureEvent(
                            request_id=request_id,
                            timestamp=datetime.now(),
                            event_type="provider_failure",
                            provider=provider_name.value,
                            error=str(error),
                        )
                    )

                    # --------------------------------------------------
                    # 3c. Non-retryable failure
                    # --------------------------------------------------

                    if not error.retryable:
                        breaker.record_failure()
                        break

                    # --------------------------------------------------
                    # 3d. Retry limit reached
                    # --------------------------------------------------

                    if attempt >= self.max_retries:
                        breaker.record_failure()
                        break

                    # --------------------------------------------------
                    # 3e. Retry same provider
                    # --------------------------------------------------

                    event_emitter.emit(
                        RetryEvent(
                            request_id=request_id,
                            timestamp=datetime.now(),
                            event_type="retry",
                            provider=provider_name.value,
                            attempt=attempt + 2,
                        )
                    )

                    await asyncio.sleep(0.1)

            # --------------------------------------------------
            # 4. Provider exhausted → fallback
            # --------------------------------------------------

            if index < len(provider_chain) - 1:

                next_provider = provider_chain[index + 1]

                event_emitter.emit(
                    FallbackEvent(
                        request_id=request_id,
                        timestamp=datetime.now(),
                        event_type="fallback",
                        from_provider=provider_name.value,
                        to_provider=next_provider.value,
                    )
                )

        # --------------------------------------------------
        # 5. Every provider failed
        # --------------------------------------------------

        raise RuntimeError("No available providers.")

    def _build_chain(
        self,
        request: GatewayRequest
    ) -> List[ProviderName]:

        # No preferred provider:
        # use the configured default chain.
        if request.preferred_provider is None:
            return list(self.default_chain)

        # Preferred provider goes first.
        provider_chain = [request.preferred_provider]

        # Add the remaining providers afterward.
        for provider in self.default_chain:
            if provider != request.preferred_provider:
                provider_chain.append(provider)

        return provider_chain