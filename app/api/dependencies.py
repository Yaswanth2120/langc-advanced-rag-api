from functools import lru_cache

from app.core.config import settings
from app.services.rag_service import AdvancedRAGEngine


@lru_cache(maxsize=1)
def get_rag_engine() -> AdvancedRAGEngine:
    return AdvancedRAGEngine(settings)
