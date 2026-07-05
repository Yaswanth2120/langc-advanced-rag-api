from datetime import datetime

from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    document_id: str
    filename: str
    file_type: str
    status: str
    # Matches the live table's timestamptz column (supabase/migrations/003).
    # Both backends feed pydantic an ISO-8601 string (local JSON stores it
    # verbatim; PostgREST serializes timestamptz to it); pydantic parses to a
    # tz-aware datetime and FastAPI serializes responses back to ISO-8601.
    # Note: Supabase rows also carry a legacy text_path field; pydantic's
    # default extra="ignore" drops it from API responses.
    created_at: datetime
