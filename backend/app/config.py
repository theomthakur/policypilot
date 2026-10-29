"""Application settings, loaded from environment variables (see .env.example)."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: Literal["development", "test", "production"] = "development"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    public_origin: str = "http://localhost:8080"
    demo_passcode: str = ""
    session_cookie_secure: bool = False

    # PostgreSQL
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "policypilot"
    postgres_user: str = "policypilot"
    postgres_password: str = "change-me"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    session_ttl_seconds: int = 86_400
    search_cache_ttl_seconds: int = 900
    ingest_status_ttl_seconds: int = 3_600

    # LLM
    llm_provider: Literal["openai_compatible", "fake"] = "openai_compatible"
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-4o-mini"
    llm_temperature: float = 0.0
    llm_seed: int | None = 42
    llm_request_timeout_s: float = 30.0
    llm_price_input_per_million: float = 0.15
    llm_price_output_per_million: float = 0.60

    # Embeddings
    embedding_provider: Literal["local", "openai", "fake"] = "local"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    # Retrieval
    chunk_tokens: int = 350
    chunk_overlap_tokens: int = 50
    search_candidates: int = 20
    search_top_k_default: int = 6
    rrf_k: int = 60
    weak_score_threshold: float = 0.02
    weak_min_cosine: float = 0.5

    # Agent limits
    agent_max_steps: int = 8
    agent_max_tool_calls: int = 6
    agent_max_query_revisions: int = 2
    agent_max_tool_retries: int = 1
    agent_tool_timeout_s: float = 8.0
    agent_turn_timeout_s: float = 60.0
    agent_max_tokens_per_turn: int = 25_000
    agent_max_pages_per_read: int = 3

    # Uploads
    upload_max_mb: int = 10
    upload_max_pages: int = 100
    upload_dir: str = "/data/uploads"
    corpus_dir: str = "/app/corpus/pdfs"
    corpus_autoload: bool = True

    # Public safety
    rate_limit_per_minute: int = 20
    daily_budget_usd: float = 1.0
    fault_injection_enabled: bool = False

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def llm_configured(self) -> bool:
        return self.llm_provider == "fake" or bool(self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
