import httpx


def main():
    url = "http://127.0.0.1:8000/v1/chat/completions"
    payload = {
        "team_id": "space-team",
        "prompt": "Write a 3 line poem about stars.",
        "stream": True,
    }
    print("Connecting to LLM Gateway SSE Stream...")
    with httpx.stream("POST", url, json=payload, timeout=30.0) as response:
        print(f"Status: {response.status_code}")
        for line in response.iter_lines():
            if line:
                print(line)


if __name__ == "__main__":
    main()
