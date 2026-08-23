from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.

    All secrets and environment-specific values should come
    from environment variables / .env rather than being hardcoded.
    """

    # Application
    app_name: str = "Civic AI"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = ""

    # API
    api_prefix: str = "/api"

    # CORS
    frontend_url: str = "http://localhost:5173"
    cors_origins: str = Field(
        default=(
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:3000,http://127.0.0.1:3000"
        ),
        description="Comma-separated list of allowed frontend origins.",
    )

    # Groq
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_temperature: float = 0.2
    groq_max_tokens: int = 4096   # agents need space for structured output
    groq_timeout_seconds: float = 45.0
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    gemini_timeout_seconds: float = 45.0

    # Agentic loop
    agent_max_iterations: int = 5  # max tool-call rounds before forcing final answer
    # JWT Authentication
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    @computed_field
    @property
    def allowed_origins(self) -> list[str]:
        origins = [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

        if self.frontend_url and self.frontend_url not in origins:
            origins.append(self.frontend_url)

        return origins

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Using a cached settings object prevents repeatedly
    reading/parsing the .env file during application runtime.
    """
    return Settings()


settings = get_settings()
