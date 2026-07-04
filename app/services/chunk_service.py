import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.services import document_service


def _chunks_file() -> Path:
    # Reuse the document service storage root so a single configure_storage()
    # call (e.g. in tests) covers documents and chunks alike.
    return document_service.STORAGE_DIR / "chunks.json"


def _read_chunks() -> list[dict]:
    chunks_file = _chunks_file()
    if not chunks_file.exists():
        return []
    with chunks_file.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_chunks(records: list[dict]) -> None:
    chunks_file = _chunks_file()
    chunks_file.parent.mkdir(parents=True, exist_ok=True)
    with chunks_file.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2)


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping character windows (pure Python, no LLM deps)."""
    if not text.strip():
        return []

    step = max(1, chunk_size - overlap)
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        window = text[start : start + chunk_size].strip()
        if window:
            chunks.append(window)
        start += step
    return chunks


def ingest_document(document_id: str) -> list[dict]:
    """Chunk a previously uploaded document's text and persist the chunks.

    Re-ingesting replaces any existing chunks for the same document. Returns
    the chunk records created for this document.
    """
    document = document_service.get_document(document_id)
    if document is None:
        raise document_service.DocumentNotFoundError(document_id)

    # Local file location is derived from the id (not stored in metadata),
    # so this works whether the metadata came from Supabase or local JSON.
    text = document_service.text_path_for(document_id).read_text(
        encoding="utf-8", errors="replace"
    )
    pieces = _split_text(text, settings.chunk_size, settings.chunk_overlap)

    created_at = datetime.now(timezone.utc).isoformat()
    new_chunks = [
        {
            "chunk_id": str(uuid.uuid4()),
            "document_id": document_id,
            "chunk_index": index,
            "text": piece,
            "created_at": created_at,
        }
        for index, piece in enumerate(pieces)
    ]

    # Replace any prior chunks for this document (idempotent re-ingest).
    others = [c for c in _read_chunks() if c["document_id"] != document_id]
    _write_chunks(others + new_chunks)

    # Embed the chunks into the Chroma collection used by /query/documents.
    from app.services import vector_store

    vector_store.index_document(document_id, new_chunks)

    return new_chunks


def list_chunks(document_id: str) -> list[dict]:
    """Return chunks for a single document, ordered by chunk_index."""
    chunks = [c for c in _read_chunks() if c["document_id"] == document_id]
    return sorted(chunks, key=lambda c: c["chunk_index"])


def all_chunks() -> list[dict]:
    """Return every stored chunk across all documents."""
    return _read_chunks()
