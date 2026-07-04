import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "LangC Advanced RAG API"
    app_version: str = "1.0.0"
    chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
    chunk_size: int = int(os.getenv("RAG_CHUNK_SIZE", "650"))
    chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "80"))
    top_k: int = int(os.getenv("RAG_TOP_K", "4"))
    relevance_threshold: float = float(os.getenv("RAG_RELEVANCE_THRESHOLD", "0.1"))
    langsmith_tracing: bool = os.getenv("LANGSMITH_TRACING", "").lower() == "true"
    supabase_url: str | None = os.getenv("SUPABASE_URL") or None
    # Anon/publishable key. NOT sufficient for server-side table access once
    # RLS is locked down (migration 002); kept for /supabase/health and as a
    # temporary fallback only.
    supabase_key: str | None = os.getenv("SUPABASE_KEY") or None
    # Service-role key (bypasses RLS; server-side ONLY). This is what the
    # backend uses to access the documents table. Never expose client-side,
    # never log it.
    supabase_service_role_key: str | None = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or None
    )
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    api_key: str | None = os.getenv("API_KEY") or None
    rate_limit: str = os.getenv("RATE_LIMIT", "30/minute")
    # Exact browser origins allowed by CORS (comma-separated). Defaults to the
    # local static-served frontend; override via CORS_ALLOW_ORIGINS in prod.
    cors_allow_origins: tuple[str, ...] = tuple(
        o.strip()
        for o in os.getenv(
            "CORS_ALLOW_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500"
        ).split(",")
        if o.strip()
    )


settings = Settings()

if settings.langsmith_tracing:
    os.environ["LANGSMITH_TRACING"] = "true"
