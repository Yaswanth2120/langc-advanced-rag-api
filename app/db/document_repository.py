"""Document metadata persistence.

When ``SUPABASE_URL`` and ``SUPABASE_KEY`` are configured, document metadata is
persisted to a Supabase ``documents`` table. Otherwise it falls back to the
local JSON store managed by ``document_service``. This keeps the Supabase
integration wired and usable in production while the app still runs with no
external database.
"""

from app.core import offline
from app.core.config import settings
from app.db.supabase_client import create_supabase_client


TABLE = "documents"

_client = None


def enabled() -> bool:
    """True when Supabase credentials are configured and offline mode is off."""
    if offline.is_offline():
        return False
    return bool(settings.supabase_url and settings.supabase_key)


def _get_client():
    global _client
    if _client is None:
        _client = create_supabase_client(settings.supabase_url, settings.supabase_key)
    return _client


def insert(record: dict) -> None:
    _get_client().table(TABLE).insert(record).execute()


def list_all() -> list[dict]:
    response = _get_client().table(TABLE).select("*").execute()
    return response.data or []


def get(document_id: str) -> dict | None:
    response = (
        _get_client()
        .table(TABLE)
        .select("*")
        .eq("document_id", document_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def delete(document_id: str) -> None:
    _get_client().table(TABLE).delete().eq("document_id", document_id).execute()


def reset_client() -> None:
    """Drop the cached Supabase client so it is rebuilt from current settings."""
    global _client
    _client = None
