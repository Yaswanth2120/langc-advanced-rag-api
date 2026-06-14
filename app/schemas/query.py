from typing import Literal

from pydantic import BaseModel, Field


RetrievalMode = Literal["basic", "multi_query", "hybrid", "agentic"]


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    mode: RetrievalMode = "hybrid"


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    mode: RetrievalMode
    rewritten_query: str | None = None
    retrieved_documents: int
