"""Document metadata persistence.

When ``SUPABASE_URL`` and ``SUPABASE_SERVICE_ROLE_KEY`` are configured, document metadata is
persisted to a Supabase ``documents`` table. Otherwise it falls back to the
local JSON store managed by ``document_service``. This keeps the Supabase
integration wired and usable in production while the app still runs with no
external database.
"""

import logging

from app.core import offline
from app.core.config import settings
from app.db.supabase_client import create_supabase_client


logger = logging.getLogger(__name__)

TABLE = "documents"

_client = None
_warned_anon = False


def _backend_key() -> str | None:
    """The key used for server-side Supabase access.

    Prefers the service-role key (bypasses RLS by design; meant for trusted
    server-to-server use). Falls back to the anon key ONLY for backwards
    compatibility — once RLS is locked down (migration 002) the anon key has
    zero access to the documents table and this fallback stops working.
    Key values are never logged.
    """
    global _warned_anon
    if settings.supabase_service_role_key:
        return settings.supabase_service_role_key
    if settings.supabase_key and not _warned_anon:
        logger.warning(
            "Supabase document persistence is using the ANON key server-side. "
            "This is deprecated and will fail once RLS is locked down "
            "(supabase/migrations/002). Set SUPABASE_SERVICE_ROLE_KEY."
        )
        _warned_anon = True
    return settings.supabase_key


def enabled() -> bool:
    """True when Supabase credentials are configured and offline mode is off."""
    if offline.is_offline():
        return False
    return bool(settings.supabase_url and _backend_key())


def _get_client():
    global _client
    if _client is None:
        _client = create_supabase_client(settings.supabase_url, _backend_key())
    return _client


def insert(record: dict) -> None:
    # record["created_at"] is a timezone-aware ISO-8601 string; Postgres casts
    # it to the table's timestamptz column on insert (migrations 001/003), and
    # reads come back as ISO-8601 strings, matching the local-JSON backend.
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
