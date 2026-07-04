from functools import lru_cache

from fastapi import Depends, Header, HTTPException

from app.core.config import settings
from app.services.rag_service import AdvancedRAGEngine


@lru_cache(maxsize=1)
def get_rag_engine() -> AdvancedRAGEngine:
    return AdvancedRAGEngine(settings)


def expected_api_key() -> str | None:
    """The server-side API key from ``API_KEY``, or None if it is unset/empty."""
    return settings.api_key


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    expected: str | None = Depends(expected_api_key),
) -> None:
    """Enforce the X-API-Key header on protected routes, failing closed.

    Behavior:
    - ``API_KEY`` unset or empty: every request is rejected with 401. Auth is
      never silently disabled — a route with no configured key is unusable, not
      open.
    - ``API_KEY`` set: a request is allowed only when its ``X-API-Key`` header
      matches; otherwise 401.
    """
    if not expected:
        # Fail closed: no server key configured -> reject all protected traffic.
        raise HTTPException(
            status_code=401,
            detail="API key auth is not configured (set API_KEY on the server).",
        )
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
