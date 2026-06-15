import math

from app.core.config import settings
from app.services import chunk_service


NO_CONTEXT_MESSAGE = "I don't have enough information in the uploaded documents."


def _tokenize(text: str) -> list[str]:
    return [
        token.strip(".,!?;:()[]{}\"'").lower()
        for token in text.split()
        if len(token.strip(".,!?;:()[]{}\"'")) > 2
    ]


def _bm25_scores(query_terms: list[str], corpus_tokens: list[list[str]]) -> list[float]:
    """Classic BM25 scoring in pure Python (k1=1.5, b=0.75)."""
    k1 = 1.5
    b = 0.75
    n_docs = len(corpus_tokens)
    if n_docs == 0:
        return []

    doc_lengths = [len(tokens) for tokens in corpus_tokens]
    avg_len = sum(doc_lengths) / n_docs if n_docs else 0.0

    # Document frequency per unique query term.
    unique_terms = set(query_terms)
    doc_freq = {
        term: sum(1 for tokens in corpus_tokens if term in tokens)
        for term in unique_terms
    }

    scores = []
    for tokens, length in zip(corpus_tokens, doc_lengths):
        term_counts: dict[str, int] = {}
        for token in tokens:
            term_counts[token] = term_counts.get(token, 0) + 1

        score = 0.0
        for term in unique_terms:
            freq = term_counts.get(term, 0)
            if freq == 0:
                continue
            df = doc_freq[term]
            idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
            denom = freq + k1 * (1 - b + b * (length / avg_len if avg_len else 0))
            score += idf * (freq * (k1 + 1)) / denom
        scores.append(score)
    return scores


def _confidence(query_terms: list[str], retrieved_tokens: list[list[str]]) -> float:
    """Fraction of distinct query terms covered by the retrieved chunks."""
    unique_terms = set(query_terms)
    if not unique_terms:
        return 0.0
    matched = {
        term
        for term in unique_terms
        if any(term in tokens for tokens in retrieved_tokens)
    }
    return round(len(matched) / len(unique_terms), 4)


def answer_question(question: str) -> dict:
    """Answer a question extractively from locally stored document chunks.

    Returns a dict with ``answer``, ``sources``, and ``confidence_score``.
    Never calls an external LLM.
    """
    query_terms = _tokenize(question)
    chunks = chunk_service.all_chunks()

    if not query_terms or not chunks:
        return {"answer": NO_CONTEXT_MESSAGE, "sources": [], "confidence_score": 0.0}

    corpus_tokens = [_tokenize(chunk["text"]) for chunk in chunks]
    scores = _bm25_scores(query_terms, corpus_tokens)

    ranked = sorted(
        ((score, idx) for idx, score in enumerate(scores) if score > 0),
        key=lambda item: item[0],
        reverse=True,
    )

    if not ranked:
        return {"answer": NO_CONTEXT_MESSAGE, "sources": [], "confidence_score": 0.0}

    top = ranked[: settings.top_k]
    top_chunks = [chunks[idx] for _, idx in top]
    top_tokens = [corpus_tokens[idx] for _, idx in top]

    answer = "\n\n".join(chunk["text"] for chunk in top_chunks)

    # Distinct document ids, preserving rank order, for cited retrieval.
    sources: list[str] = []
    for chunk in top_chunks:
        if chunk["document_id"] not in sources:
            sources.append(chunk["document_id"])

    return {
        "answer": answer,
        "sources": sources,
        "confidence_score": _confidence(query_terms, top_tokens),
    }
