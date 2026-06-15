from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_rag_engine
from app.schemas.document_query import DocumentQueryRequest, DocumentQueryResponse
from app.schemas.query import AskRequest, AskResponse
from app.services import document_qa_service
from app.services.rag_service import AdvancedRAGEngine


router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, engine: AdvancedRAGEngine = Depends(get_rag_engine)):
    try:
        result = engine.answer(request.question, request.mode)
        return AskResponse(
            answer=result.answer,
            sources=result.sources,
            mode=result.mode,
            rewritten_query=result.rewritten_query,
            retrieved_documents=result.retrieved_documents,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/query/documents", response_model=DocumentQueryResponse)
def query_documents(request: DocumentQueryRequest):
    result = document_qa_service.answer_question(request.question)
    return DocumentQueryResponse(**result)
