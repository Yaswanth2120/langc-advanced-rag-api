import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


ALLOWED_TYPES = {".txt", ".md", ".pdf"}

# Base storage location. Overridable at runtime (e.g. in tests) via
# ``configure_storage`` so uploads stay out of the repo tree.
STORAGE_DIR = Path("storage")


class UnsupportedFileTypeError(ValueError):
    """Raised when an uploaded file has an extension we do not accept."""


class DocumentNotFoundError(LookupError):
    """Raised when a document_id does not match any stored document."""


def configure_storage(base_dir: Path) -> None:
    """Point the service at a different storage root (used by tests)."""
    global STORAGE_DIR
    STORAGE_DIR = Path(base_dir)


def _uploads_dir() -> Path:
    return STORAGE_DIR / "uploads"


def _metadata_file() -> Path:
    return STORAGE_DIR / "documents.json"


def _file_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def _read_metadata() -> list[dict]:
    metadata_file = _metadata_file()
    if not metadata_file.exists():
        return []
    with metadata_file.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_metadata(records: list[dict]) -> None:
    metadata_file = _metadata_file()
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    with metadata_file.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2)


def _extract_text(path: Path, extension: str) -> str:
    if extension in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")

    # PDF
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def save_upload(filename: str, content: bytes) -> dict:
    """Validate, persist, and extract text from an uploaded document.

    Returns the stored metadata record. Raises ``UnsupportedFileTypeError``
    for disallowed extensions.
    """
    extension = _file_extension(filename)
    if extension not in ALLOWED_TYPES:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{extension or filename}'. "
            f"Allowed types: {', '.join(sorted(ALLOWED_TYPES))}."
        )

    document_id = str(uuid.uuid4())
    uploads_dir = _uploads_dir()
    uploads_dir.mkdir(parents=True, exist_ok=True)

    stored_path = uploads_dir / f"{document_id}{extension}"
    stored_path.write_bytes(content)

    text = _extract_text(stored_path, extension)
    text_path = uploads_dir / f"{document_id}.txt"
    text_path.write_text(text, encoding="utf-8")

    record = {
        "document_id": document_id,
        "filename": filename,
        "file_type": extension.lstrip("."),
        "status": "uploaded",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "stored_path": str(stored_path),
        "text_path": str(text_path),
    }

    records = _read_metadata()
    records.append(record)
    _write_metadata(records)

    return record


def list_documents() -> list[dict]:
    """Return all stored document metadata records."""
    return _read_metadata()


def get_document(document_id: str) -> dict | None:
    """Return a single document metadata record, or None if not found."""
    for record in _read_metadata():
        if record["document_id"] == document_id:
            return record
    return None
