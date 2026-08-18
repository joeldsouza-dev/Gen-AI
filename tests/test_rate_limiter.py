"""
Get test_in_memory_bucket passing before you write a single line of Redis
code. It's the cheapest possible way to validate your understanding of the
algorithm before adding network/concurrency complexity on top of it.
"""

import time

import pytest
import redis.asyncio as redis
import asyncio
from app.core.rate_limiter import InMemoryTokenBucket, RedisTokenBucket


@pytest.mark.asyncio
async def test_in_memory_bucket_allows_up_to_capacity():
    bucket = InMemoryTokenBucket(capacity=5, refill_rate_per_second=0)
    assert await bucket.allow() is True
    assert await bucket.allow() is True
    assert await bucket.allow() is True
    assert await bucket.allow() is True
    assert await bucket.allow() is True

    assert await bucket.allow() is False  # no refill, isolate the "allow" logic
    # TODO(you): assert that exactly 5 calls to bucket.allow() return True,
    # and the 6th returns False.


@pytest.mark.asyncio
async def test_in_memory_bucket_refills_over_time():
    bucket = InMemoryTokenBucket(capacity=5, refill_rate_per_second=5)  # refills fully in 1 second
    # TODO(you): drain the bucket (5 calls to allow()), confirm the 6th fails,
    # sleep ~1.1 seconds (time.sleep), then confirm allow() succeeds again.
    # (Yes, a real sleep in a test is a bit slow — that's fine for this one,
    # it's testing real elapsed-time behavior.)
    for _ in range(5):
        assert  await bucket.allow() is True

    assert await bucket.allow() is False

    await asyncio.sleep(1.1)

    assert await bucket.allow() is True


@pytest.mark.asyncio
async def test_concurrent_load_respects_limit():
    bucket = InMemoryTokenBucket(
        capacity=20,
        refill_rate_per_second=0,
    )

    async def make_request():
        return await bucket.allow()

    requests = [
        make_request()
        for _ in range(50)
    ]

    results = await asyncio.gather(*requests)

    assert sum(results) == 20


@pytest.mark.asyncio
async def test_in_memory_per_team_isolation():
    bucket = InMemoryTokenBucket(capacity=2, refill_rate_per_second=0)

    # Team A uses 2 tokens
    assert await bucket.allow("team-a") is True
    assert await bucket.allow("team-a") is True
    assert await bucket.allow("team-a") is False

    # Team B still has full capacity
    assert await bucket.allow("team-b") is True
    assert await bucket.allow("team-b") is True
    assert await bucket.allow("team-b") is False

@pytest.mark.asyncio
async def test_redis_bucket_allows_up_to_capacity():
    redis_client = redis.from_url("redis://localhost:6379/0")

    bucket = RedisTokenBucket(
        redis_client=redis_client,
        key="test:rate_limit:capacity",
        capacity=5,
        refill_rate_per_second=5,
    )

    await redis_client.delete("test:rate_limit:capacity")

    assert await bucket.allow() is True
    assert await bucket.allow() is True
    assert await bucket.allow() is True
    assert await bucket.allow() is True
    assert await bucket.allow() is True

    assert await bucket.allow() is False

    await redis_client.aclose()
@pytest.mark.asyncio
async def test_redis_bucket_refills_over_time():
    redis_client = redis.from_url("redis://localhost:6379/0")

    key = "test:rate_limit:refill"

    bucket = RedisTokenBucket(
        redis_client=redis_client,
        key=key,
        capacity=5,
        refill_rate_per_second=5,
    )

    await redis_client.delete(key)

    for _ in range(5):
        assert await bucket.allow() is True

    assert await bucket.allow() is False

    await asyncio.sleep(1.1)

    assert await bucket.allow() is True

    await redis_client.aclose()
@pytest.mark.asyncio
async def test_redis_concurrent_load_respects_limit():
    redis_client = redis.from_url("redis://localhost:6379/0")

    key = "test:rate_limit:concurrent"

    bucket = RedisTokenBucket(
        redis_client=redis_client,
        key=key,
        capacity=20,
        refill_rate_per_second=0,
    )

    await redis_client.delete(key)

    requests = [
        bucket.allow()
        for _ in range(50)
    ]

    results = await asyncio.gather(*requests)

    assert sum(results) == 20

    await redis_client.aclose()
