"""Process-wide offline switch.

When enabled, the app is forced onto its local, no-network backends: the local
hashing embeddings instead of OpenAI, and local JSON metadata instead of
Supabase — regardless of what credentials are present in the environment.

The offline evaluation runner uses this to guarantee it never makes OpenAI
calls or touches Supabase, honoring phase 4's constraint even when a real
``.env`` is present.
"""

_offline = False


def set_offline(value: bool) -> None:
    global _offline
    _offline = bool(value)


def is_offline() -> bool:
    return _offline
