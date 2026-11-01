"""Application settings, loaded from environment variables (see .env.example)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
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
    frontend_dist_dir: str = ""  # optional built UI for a single-service deployment

    # Durable jobs (docs/adr/0010): turns and ingestion run from a PostgreSQL job table.
    worker_embedded: bool = (
        True  # False when a separate worker process (python -m app.jobs.worker) runs the jobs
    )
    worker_concurrency: int = 4
    worker_poll_interval_s: float = 0.25
    job_lease_seconds: float = 90.0
    job_heartbeat_seconds: float = 20.0
    job_max_attempts: int = 3
    run_migrations_on_start: bool = True  # False when a deployment runs migrations as a separate Job

    # Authentication (docs/authentication.md). "off" keeps the shared-passcode demo gate only.
    # "oidc" requires an OpenID Connect sign-in; "test" is a fake provider, refused in production.
    auth_mode: Literal["off", "oidc", "test"] = "off"
    # A production demo behind only the shared passcode (no accounts) must be asked for by name.
    allow_passcode_only_production: bool = False
    oidc_issuer: str = ""  # e.g. http://localhost:8180/realms/policypilot
    oidc_client_id: str = "policypilot"
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = ""  # defaults to {public_origin}/api/v1/auth/callback
    oidc_internal_issuer: str = ""  # optional: reach the provider by another hostname from inside a container
    auth_secret_key: str = ""  # signs the short-lived login-flow cookie; required when auth is on
    auth_session_ttl_seconds: int = 8 * 3600
    auth_cookie_secure: bool = False

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
    llm_provider: Literal["openai_compatible", "fake", "offline"] = "openai_compatible"
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_model: str = "anthropic/claude-haiku-5.5"
    llm_temperature: float = 0.0
    llm_seed: int | None = 42
    llm_request_timeout_s: float = 30.0
    llm_price_input_per_million: float = 0.10
    llm_price_output_per_million: float = 0.50

    # Embeddings
    embedding_provider: Literal["local", "openai", "fake"] = "local"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    embedding_batch_size: int = Field(default=32, ge=1)
    embedding_threads: int | None = Field(default=None, ge=1)

    # Retrieval
    chunk_tokens: int = 200
    chunk_overlap_tokens: int = 30
    search_candidates: int = 20
    search_top_k_default: int = 6
    rrf_k: int = 60
    weak_score_threshold: float = 0.02
    weak_min_cosine: float = 0.5
    # Topicality: best similarity below this AND no keyword match at all means nothing in the library is
    # about the question (measured: off-topic questions <= 0.59, in-scope >= 0.67; see ADR 0005).
    off_topic_max_cosine: float = 0.63
    reference_score_weight: float = 0.9  # below 1: rank general reference guidance under institution policy
    off_topic_enabled: bool | None = None  # None: on only with real embeddings (fake ones carry no meaning)

    # Agent limits
    agent_max_steps: int = 8
    agent_max_tool_calls: int = 6
    agent_max_query_revisions: int = 2
    agent_max_tool_retries: int = 1
    agent_tool_timeout_s: float = 8.0
    agent_turn_timeout_s: float = 60.0
    agent_max_tokens_per_turn: int = 30_000
    agent_max_pages_per_read: int = 3
    agent_assess_model: str = (
        "openai/gpt-4o"  # a stronger model for the one judgment call; empty = same model
    )
    agent_assess_price_input_per_million: float = 2.50  # approximate list prices, for the cost estimate
    agent_assess_price_output_per_million: float = 10.00
    agent_assess_ambiguity: bool = True  # one structured check after the first search of a new question

    # Uploads
    upload_max_mb: int = 10
    upload_max_pages: int = 100
    upload_dir: str = "/data/uploads"
    # "postgres" keeps small demo uploads durable when the web host has no persistent disk.
    storage_backend: Literal["local", "s3", "postgres"] = "local"
    s3_bucket: str = "policypilot-uploads"
    s3_endpoint: str = ""  # e.g. http://minio:9000; empty for AWS
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    corpus_dir: str = "/app/corpus/pdfs"
    reference_dir: str = ""  # optional folder of real public documents, loaded as source "reference"
    corpus_autoload: bool = True

    # Public safety
    rate_limit_per_minute: int = 20
    # How many reverse proxies sit in front of the API (nginx, or Caddy in production). The client address
    # is the entry this many places from the right of X-Forwarded-For; entries further left are client-set.
    trusted_proxy_hops: int = 1
    daily_budget_usd: float = 1.0
    fault_injection_enabled: bool = False

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def off_topic_check(self) -> bool:
        if self.off_topic_enabled is not None:
            return self.off_topic_enabled
        return self.embedding_provider == "local"

    @property
    def llm_configured(self) -> bool:
        return self.llm_provider in ("fake", "offline") or bool(self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
