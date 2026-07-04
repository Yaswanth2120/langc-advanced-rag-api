"""Local RAG evaluation runner for DocuIntelAI.

Seeds a fixed in-script corpus into an isolated temporary storage directory,
runs the questions in ``questions.json`` through the ``/query/documents``
retrieval pipeline (``document_qa_service.answer_question``), and writes
``results.md``.

The runner pins offline mode for its entire run (see ``app.core.offline``), so
it makes no OpenAI calls and never touches Supabase regardless of ``.env``
contents — retrieval uses the deterministic local hashing embeddings only.

The corpus logical names below must match the ``expected_source`` values in
``questions.json``.
"""

import json
import shutil
import tempfile
import time
from pathlib import Path

from app.core import offline
from app.services import chunk_service, document_qa_service, document_service


QUESTIONS_PATH = Path(__file__).parent / "questions.json"
RESULTS_PATH = Path(__file__).parent / "results.md"

# Fixed evaluation corpus. Keys are logical names referenced by
# ``expected_source`` in questions.json.
CORPUS = {
    "voyager": (
        "The Voyager spacecraft carries a golden record containing sounds and "
        "images from Earth, launched into interstellar space as a message to "
        "any civilization that might find it."
    ),
    "falcons": (
        "Peregrine falcons hunt by diving at high speed to catch prey in "
        "mid-air. This high-speed dive is called a stoop and makes the falcon "
        "the fastest animal on the planet."
    ),
    "photosynthesis": (
        "Photosynthesis is the process by which plants convert sunlight into "
        "chemical energy, storing it as sugar while releasing oxygen into the "
        "atmosphere."
    ),
    "oceans": (
        "The Pacific Ocean is the largest and deepest ocean on Earth, covering "
        "a greater area than all of the planet's land combined."
    ),
}


def seed_corpus(corpus: dict[str, str]) -> dict[str, str]:
    """Upload and ingest each corpus document. Returns name -> document_id."""
    name_to_id: dict[str, str] = {}
    for name, text in corpus.items():
        record = document_service.save_upload(f"{name}.txt", text.encode("utf-8"))
        document_id = record["document_id"]
        chunk_service.ingest_document(document_id)
        name_to_id[name] = document_id
    return name_to_id


def load_questions(path: Path = QUESTIONS_PATH) -> list[dict]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def evaluate(questions: list[dict], name_to_id: dict[str, str]) -> dict:
    """Run every question and compute aggregate quality metrics."""
    per_question = []
    answerable = 0
    retrieval_hits = 0
    citation_hits = 0
    fallback_total = 0
    fallback_correct = 0

    for item in questions:
        question = item["question"]
        q_type = item.get("type", "answerable")

        start = time.perf_counter()
        result = document_qa_service.answer_question(question)
        latency_ms = round((time.perf_counter() - start) * 1000, 3)

        is_fallback = result["answer"] == document_qa_service.NO_CONTEXT_MESSAGE
        row = {
            "question": question,
            "type": q_type,
            "latency_ms": latency_ms,
            "sources": result["sources"],
            "confidence_score": result["confidence_score"],
            "is_fallback": is_fallback,
        }

        if q_type == "fallback":
            fallback_total += 1
            correct = is_fallback and result["sources"] == []
            fallback_correct += int(correct)
            row["passed"] = correct
        else:
            answerable += 1
            expected_id = name_to_id.get(item.get("expected_source", ""))
            retrieval_hit = expected_id is not None and expected_id in result["sources"]
            keyword_hit = all(
                kw.lower() in result["answer"].lower()
                for kw in item.get("expected_keywords", [])
            )
            citation_present = len(result["sources"]) > 0

            retrieval_hits += int(retrieval_hit)
            citation_hits += int(citation_present)
            row["retrieval_hit"] = retrieval_hit
            row["keyword_hit"] = keyword_hit
            row["citation_present"] = citation_present
            row["passed"] = retrieval_hit and keyword_hit

        per_question.append(row)

    latencies = [r["latency_ms"] for r in per_question]
    metrics = {
        "total_questions": len(questions),
        "answerable_questions": answerable,
        "fallback_questions": fallback_total,
        "retrieval_hit_rate": round(retrieval_hits / answerable, 4) if answerable else 0.0,
        "citation_presence_rate": round(citation_hits / answerable, 4) if answerable else 0.0,
        "fallback_accuracy": round(fallback_correct / fallback_total, 4) if fallback_total else 0.0,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
        "max_latency_ms": max(latencies) if latencies else 0.0,
    }

    return {"metrics": metrics, "per_question": per_question}


def format_results_md(results: dict) -> str:
    m = results["metrics"]
    lines = [
        "# DocuIntelAI RAG Evaluation Results",
        "",
        "Local extractive RAG pipeline (pure-Python BM25, no LLM, no embeddings,",
        "no vector database). Generated by `evals/run_eval.py`.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Total questions | {m['total_questions']} |",
        f"| Answerable questions | {m['answerable_questions']} |",
        f"| Fallback questions | {m['fallback_questions']} |",
        f"| Retrieval hit rate | {m['retrieval_hit_rate']:.2%} |",
        f"| Citation/source presence | {m['citation_presence_rate']:.2%} |",
        f"| Fallback accuracy | {m['fallback_accuracy']:.2%} |",
        f"| Avg latency (ms) | {m['avg_latency_ms']} |",
        f"| Max latency (ms) | {m['max_latency_ms']} |",
        "",
        "## Per-question results",
        "",
        "| Question | Type | Passed | Sources | Confidence | Latency (ms) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in results["per_question"]:
        source_count = len(r["sources"])
        lines.append(
            f"| {r['question']} | {r['type']} | {'yes' if r.get('passed') else 'no'} | "
            f"{source_count} | {r['confidence_score']} | {r['latency_ms']} |"
        )
    lines.append("")
    return "\n".join(lines)


def run(
    questions_path: Path = QUESTIONS_PATH,
    results_path: Path | None = RESULTS_PATH,
    corpus: dict[str, str] | None = None,
) -> dict:
    """Run the full eval against an isolated temp storage dir.

    Returns the results dict. If ``results_path`` is provided, also writes the
    markdown report there.
    """
    corpus = CORPUS if corpus is None else corpus
    questions = load_questions(questions_path)

    from app.services import vector_store

    tmp_dir = Path(tempfile.mkdtemp())
    original_storage = document_service.STORAGE_DIR
    original_offline = offline.is_offline()
    # Pin offline mode: no OpenAI calls, no Supabase, local embeddings only,
    # regardless of environment/.env contents (phase 4 constraint).
    offline.set_offline(True)
    document_service.configure_storage(tmp_dir)
    vector_store.reset()
    try:
        name_to_id = seed_corpus(corpus)
        results = evaluate(questions, name_to_id)
    finally:
        document_service.configure_storage(original_storage)
        vector_store.reset()
        offline.set_offline(original_offline)
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if results_path is not None:
        Path(results_path).write_text(format_results_md(results), encoding="utf-8")

    return results


def main() -> None:
    results = run()
    m = results["metrics"]
    print("DocuIntelAI RAG Evaluation")
    print(f"  Retrieval hit rate:       {m['retrieval_hit_rate']:.2%}")
    print(f"  Citation/source presence: {m['citation_presence_rate']:.2%}")
    print(f"  Fallback accuracy:        {m['fallback_accuracy']:.2%}")
    print(f"  Avg latency (ms):         {m['avg_latency_ms']}")
    print(f"  Results written to:       {RESULTS_PATH}")


if __name__ == "__main__":
    main()
