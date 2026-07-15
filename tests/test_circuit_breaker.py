"""
Write these against the state diagram in circuit_breaker.py's docstring.
If you can't tell from the test name what state transition it's checking,
rename it — that clarity is part of the exercise.
"""

import time

from app.core.circuit_breaker import CircuitBreaker, CircuitState


def test_starts_closed():
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=1)
    # TODO(you): assert breaker.state == CircuitState.CLOSED
    # and breaker.allow_request() is True
    assert breaker.state == CircuitState.CLOSED
    assert breaker.allow_request() is True


def test_opens_after_threshold_failures():
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=1)
    # TODO(you): call record_failure() 3 times, then assert state is OPEN
    # and allow_request() returns False.
    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED

    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED

    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN

    assert breaker.allow_request() is False


def test_half_opens_after_cooldown():
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=1)
    # TODO(you): trip it open (1 failure), sleep > cooldown_seconds,
    # then assert allow_request() returns True and state becomes HALF_OPEN.
    breaker.record_failure()

    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False

    time.sleep(1.1)

    assert breaker.allow_request() is True
    assert breaker.state == CircuitState.HALF_OPEN


def test_half_open_success_closes_circuit():
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=1)
    # TODO(you): trip it open, wait for cooldown, call allow_request() (moves
    # to half-open), then record_success(), then assert state is CLOSED again
    # and the failure counter has reset (verify by confirming it takes a full
    # `failure_threshold` more failures to re-open, not just 1).
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_failure()

    assert breaker.state == CircuitState.OPEN

    time.sleep(1.1)

    assert breaker.allow_request() is True
    assert breaker.state == CircuitState.HALF_OPEN

    breaker.record_success()

    assert breaker.state == CircuitState.CLOSED
    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED

    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED

    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN


def test_half_open_failure_reopens_circuit():
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=1)
    # TODO(you): trip it open, wait for cooldown, call allow_request() (half-open),
    # then record_failure(), then assert state is OPEN again and the cooldown
    # timer has restarted (i.e. allow_request() is False immediately after,
    # even though the original cooldown period alone would have elapsed).

     # CLOSED → OPEN
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN

    # Wait for cooldown
    time.sleep(1.1)

    # OPEN → HALF_OPEN
    assert breaker.allow_request() is True
    assert breaker.state == CircuitState.HALF_OPEN

    # Test request fails: HALF_OPEN → OPEN
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN

    # The cooldown must have restarted,
    # so another request should be rejected immediately.
    assert breaker.allow_request() is False

    
def test_half_open_allows_only_one_probe_request():
    breaker = CircuitBreaker(
        failure_threshold=1,
        cooldown_seconds=1,
    )

    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN

    time.sleep(1.1)

    # First request after cooldown becomes the probe request.
    assert breaker.allow_request() is True
    assert breaker.state == CircuitState.HALF_OPEN

    # Probe is still in flight, so additional requests must be rejected.
    assert breaker.allow_request() is False
    assert breaker.allow_request() is False
