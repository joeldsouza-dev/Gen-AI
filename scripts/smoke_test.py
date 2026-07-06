"""
Quick manual check that the gateway is alive and can serve a completion.
Run with the app already up (`uvicorn app.main:app --reload`):

    python scripts/smoke_test.py

Once fallback is implemented, a good manual test is: temporarily set
NVIDIA_NIM_API_KEY to garbage in your .env, restart the app, run this
script again, and confirm the response's `provider_used` / `was_fallback`
fields show it fell back to OpenRouter (or Ollama).
"""

import httpx

GATEWAY_URL = "http://localhost:8000/v1/completions"


def main():
    response = httpx.post(
        GATEWAY_URL,
        json={
            "team_id": "demo-team",
            "prompt": "Say hello in exactly one short sentence.",
        },
        timeout=30.0,
    )
    print(f"Status: {response.status_code}")
    print(response.json())


if __name__ == "__main__":
    main()
