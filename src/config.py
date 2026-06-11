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
    langsmith_tracing: bool = os.getenv("LANGSMITH_TRACING", "").lower() == "true"
    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_key: str | None = os.getenv("SUPABASE_KEY")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")


settings = Settings()

if settings.langsmith_tracing:
    os.environ["LANGSMITH_TRACING"] = "true"
