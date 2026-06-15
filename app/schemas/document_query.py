from pydantic import BaseModel, Field


class DocumentQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class DocumentQueryResponse(BaseModel):
    answer: str
    sources: list[str]
    confidence_score: float
