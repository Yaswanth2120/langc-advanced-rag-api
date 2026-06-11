from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.rag.engine import AdvancedRAGEngine
from src.schemas import AskRequest, AskResponse, HealthResponse


app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_rag_engine() -> AdvancedRAGEngine:
    return AdvancedRAGEngine(settings)


@app.get("/")
def root():
    return {
        "message": "LangC Advanced RAG API is running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
    )


@app.get("/features")
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


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    try:
        result = get_rag_engine().answer(request.question, request.mode)
        return AskResponse(
            answer=result.answer,
            sources=result.sources,
            mode=result.mode,
            rewritten_query=result.rewritten_query,
            retrieved_documents=result.retrieved_documents,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/supabase/health")
def supabase_health():
    if not settings.supabase_url or not settings.supabase_key:
        return {"configured": False, "message": "SUPABASE_URL or SUPABASE_KEY missing"}

    try:
        from supabase import create_client

        create_client(settings.supabase_url, settings.supabase_key)
        return {"configured": True, "message": "Supabase client created"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
