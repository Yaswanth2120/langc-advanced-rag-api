import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_rag_engine, require_api_key
from app.core.rate_limit import current_rate_limit, limiter
from app.schemas.document_query import DocumentQueryRequest, DocumentQueryResponse
from app.schemas.query import AskRequest, AskResponse
from app.services import document_qa_service
from app.services.rag_service import AdvancedRAGEngine


router = APIRouter()


def _sse(events) -> StreamingResponse:
    """Wrap an event-dict generator as a Server-Sent Events response.

    Each event is one ``data: <json>\\n\\n`` line. Event shapes: a leading
    ``{"type": "meta", ...}``, one or more ``{"type": "token", "text": ...}``,
    and a final ``{"type": "done"}`` (or ``{"type": "error", "detail": ...}``
    if generation fails mid-stream).
    """

    def generate():
        try:
            for event in events:
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/ask", response_model=AskResponse)
@limiter.limit(current_rate_limit)
def ask(
    request: Request,
    body: AskRequest,
    engine: AdvancedRAGEngine = Depends(get_rag_engine),
):
    if body.stream:
        return _sse(engine.stream_answer(body.question, body.mode))

    try:
        result = engine.answer(body.question, body.mode)
        return AskResponse(
            answer=result.answer,
            sources=result.sources,
            mode=result.mode,
            rewritten_query=result.rewritten_query,
            retrieved_documents=result.retrieved_documents,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/query/documents",
    response_model=DocumentQueryResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(current_rate_limit)
def query_documents(request: Request, body: DocumentQueryRequest):
    if body.stream:
        return _sse(document_qa_service.stream_answer_question(body.question))

    result = document_qa_service.answer_question(body.question)
    return DocumentQueryResponse(**result)
