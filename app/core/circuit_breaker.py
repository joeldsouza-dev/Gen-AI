"""
Circuit breaker — a state machine with exactly three states. Before writing
any code, draw this on paper:

    CLOSED --(failure_count >= threshold)--> OPEN
    OPEN --(cooldown_seconds elapsed)--> HALF_OPEN
    HALF_OPEN --(test request succeeds)--> CLOSED
    HALF_OPEN --(test request fails)--> OPEN  (reset cooldown timer)

State meanings:
  - CLOSED: normal operation. Requests go through to the provider. Every
    failure increments a counter; every success resets it to 0. If the
    counter hits `failure_threshold`, transition to OPEN.
  - OPEN: the provider is presumed down. Do NOT call it — fail fast and let
    the caller (the router) go straight to a fallback provider instead of
    wasting a timeout waiting on a provider that's known to be broken.
    After `cooldown_seconds`, transition to HALF_OPEN.
  - HALF_OPEN: allow exactly ONE test request through (this is what
    BaseProvider.health_check() is for — or you can use a real request,
    your call, but justify the choice in your ADR log). If it succeeds,
    go back to CLOSED and reset the failure counter. If it fails, go back
    to OPEN and restart the cooldown timer.

Why "allow exactly one" matters: if you let all traffic through during
HALF_OPEN, a still-broken provider gets hammered again before you know it's
actually recovered, which defeats the point of the breaker. This is a common
mistake in naive implementations — pay attention to it.

This should be built PER PROVIDER (each provider gets its own circuit
breaker instance/state) since NVIDIA NIM being down tells you nothing about
whether OpenRouter is down.

TODO(you): implement the state machine below. Start single-process/in-memory
like the rate limiter — you can always move state into Redis later if you
need the breaker to be shared across multiple gateway instances, but get the
state machine logic right first where it's easy to test and reason about.
"""

import time
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failure_threshold: int, cooldown_seconds: int):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._state = CircuitState.CLOSED
        self.failure_count = 0
        self.opened_at = None
        self.half_open_request_in_flight = False
        # TODO(you): what state do you need? (hint: current CircuitState,
        # a failure counter, and a timestamp of when it last opened)

    def record_success(self) -> None:
        """Call this after a provider call succeeds."""
        # TODO(you): implement the CLOSED-reset and HALF_OPEN->CLOSED transitions.
        self._state = CircuitState.CLOSED
        self.half_open_request_in_flight = False
        self.failure_count = 0
        self.opened_at = None

    def record_failure(self) -> None:
        """Call this after a provider call fails."""
        self.half_open_request_in_flight = False
        # TODO(you): implement the CLOSED->OPEN and HALF_OPEN->OPEN transitions.
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self.opened_at = time.monotonic()
            return

        if self._state == CircuitState.CLOSED:
            self.failure_count += 1

            if self.failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self.opened_at = time.monotonic()

    def allow_request(self) -> bool:
        """
        Called by the router BEFORE calling the provider.
        Return False if the circuit is OPEN (and cooldown hasn't elapsed) —
        the router should skip straight to a fallback provider in that case.
        Return True if CLOSED, or if OPEN but cooldown has elapsed (in which
        case you should transition to HALF_OPEN as a side effect here).
        """
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self.opened_at

            if elapsed >= self.cooldown_seconds:
                self._state = CircuitState.HALF_OPEN
                return True

            return False

        if self._state == CircuitState.HALF_OPEN:
            return False
        # TODO(you): implement, including the OPEN -> HALF_OPEN transition
        # based on elapsed cooldown time.
        raise NotImplementedError("Implement CircuitBreaker.allow_request()")

    @property
    def state(self) -> CircuitState:
        return self._state 
        # TODO(you): expose current state (useful for logging/dashboard/tests)
        raise NotImplementedError("Implement CircuitBreaker.state")
