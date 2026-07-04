"""Grounded question answering over uploaded documents.

Retrieval goes through a single path: the Chroma vector store populated at
ingest time (``vector_store``). Chunks scoring below the configured relevance
threshold are discarded; if nothing clears the bar the service returns a
fallback message with no sources.

Answer generation uses the OpenAI chat model when configured
(``rag_backends.get_llm``), grounded strictly in the retrieved chunks. Without
an OpenAI key it falls back to an extractive answer stitched from those same
chunks, so the endpoint works offline and deterministically.
"""

from app.core.config import settings
from app.services import rag_backends, vector_store
from app.services.rag_prompts import ANSWER_TEMPLATE


NO_CONTEXT_MESSAGE = "I don't have enough information in the uploaded documents."


def _retrieve(question: str):
    """Return retrieved (document, score) pairs that clear the relevance bar."""
    results = vector_store.search(question, k=settings.top_k)
    return [
        (doc, score)
        for doc, score in results
        if score >= settings.relevance_threshold
    ]


def _sources(docs) -> list[str]:
    """Distinct document ids in rank order, for cited retrieval."""
    sources: list[str] = []
    for doc in docs:
        document_id = doc.metadata.get("document_id")
        if document_id and document_id not in sources:
            sources.append(document_id)
    return sources


def _generate_answer(question: str, docs) -> str:
    context = "\n\n".join(doc.page_content for doc in docs)

    llm = rag_backends.get_llm()
    if llm is None:
        # Offline fallback: extractive answer from the retrieved chunks.
        return context

    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate

    chain = ChatPromptTemplate.from_template(ANSWER_TEMPLATE) | llm | StrOutputParser()
    return chain.invoke({"context": context, "question": question})


def answer_question(question: str) -> dict:
    """Answer a question from ingested document chunks via vector retrieval.

    Returns a dict with ``answer``, ``sources``, and ``confidence_score``.
    """
    retrieved = _retrieve(question)

    if not retrieved:
        return {"answer": NO_CONTEXT_MESSAGE, "sources": [], "confidence_score": 0.0}

    docs = [doc for doc, _ in retrieved]
    top_score = max(score for _, score in retrieved)

    return {
        "answer": _generate_answer(question, docs),
        "sources": _sources(docs),
        "confidence_score": round(float(top_score), 4),
    }
