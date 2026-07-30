"""
The router — where everything else in this project gets wired together.
By the time you write this file, rate_limiter.py and circuit_breaker.py
should already be implemented and tested in isolation.

Responsibilities of `route_request()`:
  1. Check the rate limiter for this team_id. If not allowed -> raise/return
     a 429-equivalent immediately. Don't even look at providers yet.
  2. Build a fallback chain: [preferred_provider (if set), then the rest in
     some sensible default order, e.g. NVIDIA_NIM -> OPENROUTER -> OLLAMA].
  3. For each provider in the chain, in order:
       a. Check that provider's circuit breaker via `allow_request()`.
          If False, skip it (don't even try) and move to the next provider.
       b. If True, call `provider.call(request)`.
       c. On success: call `breaker.record_success()`, return the
          GatewayResponse (set `was_fallback=True` if this wasn't the first
          provider tried).
       d. On ProviderError: call `breaker.record_failure()`. If
          `error.retryable` is False, or you've already retried this
          provider once, move to the next provider in the chain. If
          `error.retryable` is True and you haven't retried yet, you may
          retry the SAME provider once with a short backoff before moving
          on (this is the "retry before fallback" step from the project
          spec — keep it simple, e.g. one retry with a fixed short delay).
  4. If every provider in the chain fails, raise a clear error that the
     API layer can turn into a 502/503 response — don't let a provider's
     raw exception leak up to the caller.

Also worth logging/tracing at each step (this is what your OpenTelemetry
spans should wrap): which provider was tried, whether the breaker allowed
it, whether it succeeded, and total time spent finding a working provider.
That trace is literally the demo for this project — "watch it fail over."

TODO(you): implement `GatewayRouter` below. The pieces (providers, rate
limiter, circuit breakers) are all built already at this point — this file
is about getting the control flow and error handling right, which is its
own real skill (this is the same shape of problem as your Razorpay webhook
retry/reconciliation logic, if that's a useful anchor).
"""

import asyncio
from itertools import chain
from typing import Dict, List

from httpx import request

from app.core.circuit_breaker import CircuitBreaker
from app.core.models import GatewayRequest, GatewayResponse, ProviderError, ProviderName, RateLimitError
from app.core.rate_limiter import InMemoryTokenBucket
from app.providers.base import BaseProvider


class GatewayRouter:
    def __init__(
        self,
        providers: Dict[ProviderName, BaseProvider],
        circuit_breakers: Dict[ProviderName, CircuitBreaker],
        rate_limiter,  # your bucket implementation, keyed per team_id
        default_chain: List[ProviderName],
        max_retries: int = 2,
    ):
        self.providers = providers
        self.circuit_breakers = circuit_breakers
        self.rate_limiter = rate_limiter
        self.max_retries = max_retries
        self.default_chain = default_chain

    async def route_request(self, request: GatewayRequest) -> GatewayResponse:
        allowed = await self.rate_limiter.allow(request.team_id)
        if not allowed:
            raise RateLimitError(f"Rate limit exceeded for team {request.team_id}", retryable=False)
        chain = self._build_chain(request)
        for provider_name in chain:
            breaker = self.circuit_breakers[provider_name]

            if not breaker.allow_request():
               continue

            provider = self.providers[provider_name]
            total_attempts = 1 + self.max_retries  # 1 initial try + max_retries
            for attempt in range(total_attempts):

               try:
                  response = await provider.call(request)
                  breaker.record_success()
                  return response
               except ProviderError as error:
                  # Move to the next provider in the chain
                  if not error.retryable or attempt >= self.max_retries:
                     breaker.record_failure()
                     break  # Move to the next provider in the chain
                  # else:
                  #    # Retry the same provider after a short backoff
                  #    await asyncio.sleep(0.1)  # Simple fixed backoff for demonstration
        raise RuntimeError("No available providers.")
         
         




        

        # TODO(you): implement the full flow described in the docstring above.

    def _build_chain(self, request: GatewayRequest) -> List[ProviderName]:
        
      if request.preferred_provider is None:
         return list(self.default_chain)

      chain = [request.preferred_provider]

      for provider in self.default_chain:
         if provider != request.preferred_provider:
            chain.append(provider)
      return chain
