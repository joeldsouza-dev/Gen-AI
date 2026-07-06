"""
Central configuration, loaded once from environment variables (.env).

This file is done for you — it's pure wiring. Import `settings` anywhere
you need a config value instead of calling os.environ directly, so there's
a single source of truth and it's easy to see everything the app depends on.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # NVIDIA NIM
    nvidia_nim_api_key: str = ""
    nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_nim_model: str = "meta/llama-3.1-70b-instruct"

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Rate limiting
    default_requests_per_minute: int = 20
    default_tokens_per_minute: int = 20000

    # Circuit breaker
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_cooldown_seconds: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
