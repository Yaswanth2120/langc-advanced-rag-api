from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    document_id: str
    filename: str
    file_type: str
    status: str
    # ISO-8601 string in both storage backends. The app writes
    # datetime.now(timezone.utc).isoformat(); local JSON stores that string
    # verbatim, and Supabase stores it as timestamptz (see
    # supabase/migrations/003) which PostgREST serializes back to an ISO-8601
    # string. Kept as str so both backends round-trip identically.
    created_at: str
