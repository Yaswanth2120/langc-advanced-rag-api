"""Chroma vector store for uploaded-document retrieval.

Uploaded document chunks are embedded into a persistent Chroma collection at
ingest time; ``/query/documents`` retrieves from it via similarity search.
The collection lives under the active storage root, so tests that repoint
storage (``document_service.configure_storage``) stay fully isolated.

Embeddings come from ``rag_backends`` (OpenAI in production, a deterministic
local backend offline).
"""

from app.services import document_service, rag_backends


COLLECTION_NAME = "documents"

# Cache Chroma handles by persist path so ingest and query in the same process
# share one collection without reopening it on every call.
_stores: dict[str, object] = {}


def _persist_dir() -> str:
    return str(document_service.STORAGE_DIR / "chroma")


def _collection_name() -> str:
    # Namespace the collection by embedding backend. OpenAI embeddings (1536-d)
    # and the local hashing embeddings (4096-d) have different dimensions; a
    # single Chroma collection fixes its dimension at creation, so mixing them
    # would raise a dimension-mismatch error. Separate collections keep a
    # persisted store valid across backend switches (each backend re-ingests
    # into its own collection).
    return f"{COLLECTION_NAME}_{rag_backends.embedding_backend_name()}"


def _get_store():
    from langchain_chroma import Chroma

    persist_dir = _persist_dir()
    collection = _collection_name()
    cache_key = f"{persist_dir}::{collection}"
    store = _stores.get(cache_key)
    if store is None:
        store = Chroma(
            collection_name=collection,
            embedding_function=rag_backends.get_embeddings(),
            persist_directory=persist_dir,
            collection_metadata={"hnsw:space": "cosine"},
        )
        _stores[cache_key] = store
    return store


def index_document(document_id: str, chunks: list[dict]) -> None:
    """Embed a document's chunks into the collection, replacing any prior ones."""
    store = _get_store()

    # Idempotent re-ingest: drop this document's existing vectors first.
    try:
        store._collection.delete(where={"document_id": document_id})
    except Exception:
        # An empty/new collection has nothing to delete; ignore.
        pass

    if not chunks:
        return

    store.add_texts(
        texts=[chunk["text"] for chunk in chunks],
        metadatas=[
            {
                "document_id": document_id,
                "chunk_id": chunk["chunk_id"],
                "chunk_index": chunk["chunk_index"],
            }
            for chunk in chunks
        ],
        ids=[chunk["chunk_id"] for chunk in chunks],
    )


def search(query: str, k: int) -> list[tuple[object, float]]:
    """Return up to ``k`` (Document, relevance_score) pairs for the query."""
    store = _get_store()
    return store.similarity_search_with_relevance_scores(query, k=k)


def reset() -> None:
    """Drop cached store handles (used by tests between storage swaps)."""
    _stores.clear()
