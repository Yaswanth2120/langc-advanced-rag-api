from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    document_id: str
    filename: str
    file_type: str
    status: str
    created_at: str
