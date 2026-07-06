# LLM Gateway — Build Log

A gateway that sits in front of NVIDIA NIM, OpenRouter, and local Ollama, and:
- normalizes requests/responses across providers
- rate-limits per "team" (token bucket)
- falls back to another provider when the primary fails
- opens a circuit breaker when a provider is consistently failing
- traces every request with OpenTelemetry

## Philosophy of this scaffold

This repo is **intentionally incomplete**. Every file that contains real logic
(rate limiter, circuit breaker, fallback routing, provider calls) has a
docstring explaining *what it must do and why*, plus a `raise NotImplementedError`
or a `# TODO` where you write the actual code yourself.

What's already done for you is the boring wiring: FastAPI app boot,
config loading, Pydantic schemas, folder structure, Docker Compose for Redis.
That's not where the learning is — the learning is in the four TODO files below.

## Build order (don't skip ahead)

1. **`app/providers/base.py`** — read it first. This is the contract every
   provider must satisfy. Understand it before writing any provider.
2. **`app/providers/ollama.py`** — implement this first since it's local and
   free to hammer with test requests. Get one provider working end-to-end
   before adding the other two.
3. **`app/providers/nvidia_nim.py`** and **`app/providers/openrouter.py`** —
   same interface, different HTTP details. Once Ollama works, these are
   mostly "read the provider's API docs and match the contract."
4. **`app/core/rate_limiter.py`** — implement token bucket **in plain Python
   first** (see the docstring), get it passing the tests in
   `tests/test_rate_limiter.py`, *then* port it to Redis. Doing it in-memory
   first is what makes the Redis version make sense — you'll understand
   exactly why atomicity matters once you see it break under concurrency.
5. **`app/core/circuit_breaker.py`** — implement the closed → open → half-open
   state machine. Write out the state diagram on paper before coding it.
6. **`app/core/router.py`** — wire it all together: pick a provider, check
   the circuit breaker, check the rate limit, call the provider, fall back
   on failure. This file is mostly orchestration once the pieces above work.
7. **`app/api/routes.py`** — expose it over HTTP. This part is basically
   done for you; it just calls the router.

## Running locally

```bash
cp .env.example .env          # fill in your NVIDIA_NIM_API_KEY and OPENROUTER_API_KEY
docker compose up -d          # starts Redis
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then hit it:
```bash
python scripts/smoke_test.py
```

## Testing philosophy

`tests/` contains test *skeletons* — the assertions describing desired
behavior are partially written, but some are left as `# TODO: assert ...`
for you to fill in once you know what "correct" looks like for your own
implementation. Writing the assertion *before* the implementation (or right
alongside it) is a good habit to keep across all three projects.

## What "done" looks like for this project

- [ ] All three providers work individually (`scripts/smoke_test.py` passes for each)
- [ ] Token bucket rate limiter enforces limits under concurrent load (write a
      test that fires 50 concurrent requests and checks the count that got through)
- [ ] Circuit breaker opens after N consecutive failures and half-opens after cooldown
- [ ] Killing the primary provider (or setting a bad API key temporarily) causes
      automatic fallback to the secondary, and you can *see* this happen in the logs/traces
- [ ] A basic Grafana dashboard shows request count, error rate, and latency per provider
