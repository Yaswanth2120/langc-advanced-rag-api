from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.dependencies import require_api_key
from app.schemas.chunk import Chunk
from app.schemas.document import DocumentMetadata
from app.services import chunk_service, document_service


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/upload", response_model=DocumentMetadata)
async def upload_document(file: UploadFile = File(...)):
    content = await file.read()
    try:
        record = document_service.save_upload(file.filename, content)
    except document_service.UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return DocumentMetadata(**record)


@router.get("", response_model=list[DocumentMetadata])
def list_documents():
    return [DocumentMetadata(**record) for record in document_service.list_documents()]


@router.post("/{document_id}/ingest", response_model=list[Chunk])
def ingest_document(document_id: str):
    try:
        chunks = chunk_service.ingest_document(document_id)
    except document_service.DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found") from exc

    return [Chunk(**record) for record in chunks]


@router.get("/{document_id}/chunks", response_model=list[Chunk])
def list_document_chunks(document_id: str):
    if document_service.get_document(document_id) is None:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

    return [Chunk(**record) for record in chunk_service.list_chunks(document_id)]
