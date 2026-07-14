"""
Token bucket rate limiter — per README build order, do this in TWO stages.

STAGE 1 — plain Python, in-memory, single process.
    Implement `InMemoryTokenBucket` completely, and get
    tests/test_rate_limiter.py::test_in_memory_bucket passing, BEFORE touching
    Redis at all. This is where you actually learn what a token bucket is:

    The algorithm (don't look this up in a library, derive it from this
    description):
      - A bucket holds up to `capacity` tokens.
      - Tokens refill continuously at `refill_rate` tokens per second
        (not in discrete per-minute chunks — compute elapsed time since the
        last refill and add `elapsed_seconds * refill_rate` tokens, capped
        at `capacity`).
      - A request that wants `n` tokens is allowed if the bucket currently
        has >= n tokens available, in which case n tokens are deducted.
      - Otherwise it's rejected (or should wait, depending on your API design
        — for this project, rejecting with a 429 is simpler and matches
        real gateway behavior).

    Think about: what do you store, and when do you update it? A naive
    "tokens = tokens + elapsed * rate" computed lazily on each check call
    (rather than a background thread ticking every second) is simpler and
    is the standard approach — implement it that way.

STAGE 2 — port to Redis, so the limiter works across multiple gateway
    processes/instances, not just in one Python process's memory.

    This is where it gets genuinely tricky: "check if tokens >= n, then
    decrement" is two operations, and if two requests hit this code at the
    same time on different processes, both can read "tokens = 5, n = 5,
    allowed" before either decrements — a classic race condition.

    You have two honest options, pick one and be able to explain why:
      (a) A Redis Lua script (via EVAL) that does the check-and-decrement
          as one atomic operation on the Redis server itself.
      (b) Redis `MULTI`/`EXEC` with `WATCH` for optimistic locking.

    Look up "Redis rate limiting Lua script" for the pattern, but write your
    own — don't paste one in blind. Test it by firing 50 concurrent requests
    (see tests/test_rate_limiter.py::test_concurrent_load) and confirming the
    count that gets through matches your configured limit, not more.
"""

import time
import asyncio
import pytest

class InMemoryTokenBucket:
    """Stage 1: implement this fully before touching Redis."""

    def __init__(self, capacity: int, refill_rate_per_second: float):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_second
        self.tokens = capacity
        self.last_refill_time = time.monotonic()
        # TODO(you): what state do you need to track? (hint: current token
        # count, and the last time you computed a refill)

    async def allow(self, tokens_requested: int = 1) -> bool:
        """
        Return True and deduct tokens if enough are available, else return
        False and deduct nothing.
        """
        # TODO(you): implement the refill-then-check-then-deduct logic
        # described in the module docstring.
        current_time = time.monotonic()
        elapsed_time = current_time - self.last_refill_time
        refill_amount = elapsed_time * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + refill_amount)  
        self.last_refill_time = current_time

        if self.tokens >= tokens_requested:
            self.tokens -= tokens_requested
            return True
        else:
            return False
        

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
    


class RedisTokenBucket:
    """Stage 2: only start this once InMemoryTokenBucket's tests pass."""
    LUA_SCRIPT = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local tokens_requested = tonumber(ARGV[3])

        local redis_time= redis.call('TIME')
        local current_time = tonumber(redis_time[1]) + tonumber(redis_time[2]) /1000000
        local bucket = redis.call(
            "HMGET",
            key,
            "tokens",
            "last_refill_time"
        )

        local tokens = tonumber(bucket[1])
        local last_refill_time = tonumber(bucket[2])
        if tokens == nil or last_refill_time == nil then
            tokens = capacity
            last_refill_time = current_time
        end
        local elapsed = current_time - last_refill_time

        local refilled_tokens = elapsed * refill_rate

        tokens = math.min(
            capacity,
            tokens + refilled_tokens
        )
        local allowed = 0

        if tokens >= tokens_requested then
            tokens = tokens - tokens_requested
            allowed = 1
        end

        redis.call(
            "HMSET",
            key,
            "tokens",
            tokens,
            "last_refill_time",
            current_time
        )

        return allowed
    """  

    def __init__(self, redis_client, key: str, capacity: int, refill_rate_per_second: float):
        self.redis = redis_client
        self.key = key
        self.capacity = capacity
        self.refill_rate = refill_rate_per_second

    async def allow(self, tokens_requested: int = 1) -> bool:
        result = await self.redis.eval(
        self.LUA_SCRIPT,
        1,
        self.key,
        self.capacity,
        self.refill_rate,
        tokens_requested,
        )
        return bool(result)  # Redis returns 1 for True, 0 for False
        # TODO(you): implement atomically (Lua script or WATCH/MULTI/EXEC).
        # This must give the same correctness guarantee as the in-memory
        # version, but under concurrent access from multiple processes.
        raise NotImplementedError("Implement RedisTokenBucket.allow()")
    
