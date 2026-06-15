from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.document import DocumentMetadata
from app.services import document_service


router = APIRouter(prefix="/documents", tags=["documents"])


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
