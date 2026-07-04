"""Backend selection for document-QA embeddings and answer generation.

When ``OPENAI_API_KEY`` is configured (and offline mode is not forced) the
production backend is used: OpenAI embeddings (matching ``AdvancedRAGEngine``'s
embedding config) and an OpenAI chat model for answer generation.

Otherwise a local, deterministic, offline fallback is used: hashing embeddings
plus an extractive answer. This fallback has materially lower retrieval quality
than real embeddings, so its use is made loud rather than silent: a warning is
logged and ``/features`` reports ``embedding_backend: "local_hash"``.
"""

import logging

from app.core import offline
from app.core.config import settings
from app.services.local_embeddings import LocalHashingEmbeddings


logger = logging.getLogger(__name__)

_warned_local = False


def use_openai() -> bool:
    """True when the OpenAI backend should be used (key set, not forced offline)."""
    return (not offline.is_offline()) and bool(settings.openai_api_key)


def embedding_backend_name() -> str:
    """Name of the active embedding backend: ``"openai"`` or ``"local_hash"``."""
    return "openai" if use_openai() else "local_hash"


def _warn_local_once() -> None:
    global _warned_local
    if not _warned_local:
        logger.warning(
            "Document-QA is using the LOCAL hashing embedding fallback "
            "(OPENAI_API_KEY not set or offline mode forced). Retrieval quality "
            "is degraded compared to OpenAI embeddings. Set OPENAI_API_KEY for "
            "production use."
        )
        _warned_local = True


def get_embeddings():
    """Return the embeddings object for the document-QA vector store."""
    if use_openai():
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=settings.embedding_model)

    _warn_local_once()
    return LocalHashingEmbeddings()


def get_llm():
    """Return the chat model used to generate grounded answers, or None locally.

    When the OpenAI backend is not active there is no LLM; the document-QA
    service falls back to an extractive answer built from the retrieved chunks.
    """
    if not use_openai():
        return None

    from langchain.chat_models import init_chat_model

    return init_chat_model(
        model=settings.chat_model,
        temperature=settings.temperature,
    )
