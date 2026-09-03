from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "EarningsPulse API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS — include 127.0.0.1 for CI/Playwright (GitHub Actions uses both hostnames)
    frontend_url: str = "http://localhost:3000"
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # LLM
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    llm_model: str = "gpt-4o"

    # Hackathon partners
    tavily_api_key: str | None = None

    # Market data
    finnhub_api_key: str | None = None

    # SEC EDGAR (required User-Agent per SEC policy)
    sec_user_agent: str = "EarningsPulse earningspulse@example.com"

    # Cache
    cache_ttl_seconds: int = 300

    # PRISM (Block Convey)
    prism_api_key: str | None = None
    prism_project_id: str | None = None
    prism_host: str = "https://api.prism.blockconvey.com"
    trace_log_dir: str = "logs/traces"
    demo_cache_dir: str = "demo"

    # Optional cache
    redis_url: str | None = None

    @property
    def prism_enabled(self) -> bool:
        return bool(self.prism_api_key and self.prism_project_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()
