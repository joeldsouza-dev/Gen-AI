"""
Get test_in_memory_bucket passing before you write a single line of Redis
code. It's the cheapest possible way to validate your understanding of the
algorithm before adding network/concurrency complexity on top of it.
"""

import time

import pytest

from app.core.rate_limiter import InMemoryTokenBucket


def test_in_memory_bucket_allows_up_to_capacity():
    bucket = InMemoryTokenBucket(capacity=5, refill_rate_per_second=0)  # no refill, isolate the "allow" logic
    # TODO(you): assert that exactly 5 calls to bucket.allow() return True,
    # and the 6th returns False.


def test_in_memory_bucket_refills_over_time():
    bucket = InMemoryTokenBucket(capacity=5, refill_rate_per_second=5)  # refills fully in 1 second
    # TODO(you): drain the bucket (5 calls to allow()), confirm the 6th fails,
    # sleep ~1.1 seconds (time.sleep), then confirm allow() succeeds again.
    # (Yes, a real sleep in a test is a bit slow — that's fine for this one,
    # it's testing real elapsed-time behavior.)


@pytest.mark.asyncio
async def test_concurrent_load_respects_limit():
    """
    This is the test that actually proves you understand the race condition
    problem. Fire N concurrent requests (asyncio.gather) against a bucket
    with a known small capacity and confirm the number that succeed is
    exactly the capacity — not more.

    Do this against InMemoryTokenBucket first (should already be correct
    if your Python-level logic is right, since there's no real parallelism
    within a single asyncio event loop calling a synchronous method).

    Then write the equivalent test against RedisTokenBucket once you've
    implemented it, ideally using multiple actual OS processes or at least
    being honest with yourself about what asyncio concurrency does and
    doesn't prove about real distributed concurrency.
    """
    # TODO(you): implement using asyncio.gather with e.g. 50 concurrent
    # calls to bucket.allow() against a bucket with capacity=20, and assert
    # sum(results) == 20.
    pass
