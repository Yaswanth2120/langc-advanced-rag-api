from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.db.supabase_client import create_supabase_client
from app.schemas.health import HealthResponse


router = APIRouter()


@router.get("/")
def root():
    return {
        "message": "LangC Advanced RAG API is running",
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
    )


@router.get("/features")
def features():
    return {
        "retrieval_modes": {
            "basic": "Vector similarity retrieval",
            "multi_query": "LLM-generated query variations for better recall",
            "hybrid": "Vector retrieval plus keyword retrieval",
            "agentic": "Hybrid retrieval with relevance check, rewrite, and retry",
        },
        "observability": "LangSmith tracing when LANGSMITH_TRACING=true",
        "optional_storage": "Supabase can be configured for persistence",
    }


@router.get("/supabase/health")
def supabase_health():
    if not settings.supabase_url or not settings.supabase_key:
        return {"configured": False, "message": "SUPABASE_URL or SUPABASE_KEY missing"}

    try:
        create_supabase_client(settings.supabase_url, settings.supabase_key)
        return {"configured": True, "message": "Supabase client created"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
