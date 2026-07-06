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


class InMemoryTokenBucket:
    """Stage 1: implement this fully before touching Redis."""

    def __init__(self, capacity: int, refill_rate_per_second: float):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_second
        # TODO(you): what state do you need to track? (hint: current token
        # count, and the last time you computed a refill)

    def allow(self, tokens_requested: int = 1) -> bool:
        """
        Return True and deduct tokens if enough are available, else return
        False and deduct nothing.
        """
        # TODO(you): implement the refill-then-check-then-deduct logic
        # described in the module docstring.
        raise NotImplementedError("Implement InMemoryTokenBucket.allow()")


class RedisTokenBucket:
    """Stage 2: only start this once InMemoryTokenBucket's tests pass."""

    def __init__(self, redis_client, key: str, capacity: int, refill_rate_per_second: float):
        self.redis = redis_client
        self.key = key
        self.capacity = capacity
        self.refill_rate = refill_rate_per_second

    async def allow(self, tokens_requested: int = 1) -> bool:
        # TODO(you): implement atomically (Lua script or WATCH/MULTI/EXEC).
        # This must give the same correctness guarantee as the in-memory
        # version, but under concurrent access from multiple processes.
        raise NotImplementedError("Implement RedisTokenBucket.allow()")
