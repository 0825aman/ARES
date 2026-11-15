from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./maar_dev.db"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://127.0.0.1:3000,http://127.0.0.1:3001"
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    UPLOAD_DIR: str = "./uploads"
    EXPORT_DIR: str = "./exports"
    MAX_UPLOAD_SIZE_MB: int = 20
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: int = 120
    WATSONX_URL: str = ""
    WATSONX_PROJECT_ID: str = ""
    WATSONX_API_KEY: str = ""
    WATSONX_MODEL: str = "meta-llama/llama-3-3-70b-instruct"
    SEARCH_PROVIDER: str = "tavily"
    SEARCH_API_KEY: str = ""
    SEARCH_MAX_RESULTS: int = 8
    WEB_FETCH_TIMEOUT_SECONDS: int = 15
    WEB_FETCH_MAX_CONTENT_KB: int = 200
    LLM_CONTEXT_BUDGET_CHARS: int = 60000
    # ── Fallback LLM providers ───────────────────────────────────────────────
    # Comma-separated list of fallback providers to try on rate-limit (429).
    # Example: "groq" or "groq,openai"
    FALLBACK_LLM_PROVIDERS: str = ""
    # Groq fallback settings (used when "groq" is in FALLBACK_LLM_PROVIDERS)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    # OpenAI fallback settings (used when "openai" is in FALLBACK_LLM_PROVIDERS)
    OPENAI_API_KEY: str = ""
    OPENAI_FALLBACK_MODEL: str = "gpt-4o-mini"
    # Gemini fallback settings (used when "gemini" is in FALLBACK_LLM_PROVIDERS)
    # Get a free key at: https://aistudio.google.com/app/apikey
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    # OpenRouter fallback settings (used when "openrouter" is in FALLBACK_LLM_PROVIDERS)
    # Free models available — get key at: https://openrouter.ai/keys
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "meta-llama/llama-3.1-8b-instruct"
    # ── Phase 5: Human in the loop ───────────────────────────────────────────
    REQUIRE_HUMAN_APPROVAL: bool = False
    # ── Phase 3: Multi-agent settings ────────────────────────────────────────
    MAX_SUPERVISOR_CYCLES: int = 30
    MAX_RESEARCH_TASKS: int = 20
    CHECKPOINT_DB_URL: str = "./maar_checkpoints.db"
    LOG_FORMAT: str = "text"
    # ── Phase 4: Source collection ────────────────────────────────────────────
    ARXIV_ENABLED: bool = False
    SEMANTIC_SCHOLAR_API_KEY: str = ""
    # ── Phase 4: Claim verification ───────────────────────────────────────────
    VERIFICATION_DEPTH: str = "basic"
    MAX_CLAIMS_PER_RUN: int = 20
    # ── Phase 4: Critic Agent ─────────────────────────────────────────────────
    CRITIC_MAX_REVIEW_CYCLES: int = 2
    # ── Phase 4: LLM usage tracking ──────────────────────────────────────────
    ENABLE_LLM_USAGE_TRACKING: bool = True
    LLM_COST_PER_1K_TOKENS: float = 0.0
    # ── Phase 6: Database reliability ────────────────────────────────────────
    DB_WAL_MODE: bool = True
    DB_BUSY_TIMEOUT_MS: int = 5000
    # ── Phase 6: Retry configuration ─────────────────────────────────────────
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_BASE_DELAY_S: float = 1.0
    # ── Phase 6: Authentication ───────────────────────────────────────────────
    AUTH_SECRET_KEY: str = ""
    SESSION_TTL_HOURS: int = 8
    AUTO_LOGIN_DEV: bool = False
    ADMIN_USERNAME: str = "admin"
    # Store as bcrypt hash. Generate with: python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
    # Leave empty to trigger a warning on startup (insecure — no auth enforced).
    ADMIN_PASSWORD_HASH: str = ""
    # Maximum failed login attempts before lockout
    AUTH_MAX_ATTEMPTS: int = 5
    # Lockout duration in minutes
    AUTH_LOCKOUT_MINUTES: int = 15
    # NOTE: LANGCHAIN_TRACING_V2, LANGCHAIN_API_KEY, LANGCHAIN_PROJECT, and
    # LANGCHAIN_ENDPOINT are NOT defined here — they are read directly by the
    # langsmith library from OS env vars. Adding them to Settings would create
    # a dependency that contradicts the requirement that ARES works without
    # any LangSmith configuration.

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()


def get_allowed_origins() -> list[str]:
    origins: list[str] = []
    for origin in settings.ALLOWED_ORIGINS.split(","):
        o = origin.strip()
        if not o:
            continue
        if not o.startswith("http://") and not o.startswith("https://"):
            if ".onrender.com" in o:
                o = f"https://{o}"
            else:
                o = f"https://{o}.onrender.com"
        origins.append(o)
    return origins
