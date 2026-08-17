"""RAG evaluation runner for DocuIntelAI.

Seeds a fixed in-script corpus into an isolated temporary storage directory,
runs the questions in ``questions.json`` through the real ``/query/documents``
retrieval pipeline (``document_qa_service.answer_question`` -> Chroma ->
``rag_backends``), and writes a results report.

Two modes:

- ``run()`` (default, used by ``make eval`` and CI): pins offline mode (see
  ``app.core.offline``), so it makes no OpenAI calls and never touches
  Supabase regardless of ``.env`` contents. Retrieval uses the deterministic
  local hashing embeddings (cosine similarity over hashed bag-of-words
  vectors, NOT BM25 and NOT a real embedding model) and an extractive
  "answer" (the retrieved context verbatim, no LLM). This is a fast,
  zero-cost, fully reproducible smoke test of the retrieval plumbing — it
  intentionally does NOT measure production answer quality.
- ``run(live=True)`` (``make eval-live``): uses whatever backend is actually
  configured in the environment. With ``OPENAI_API_KEY`` set, this exercises
  real OpenAI embeddings + chat generation end to end — the only mode that
  measures what a deployed user actually experiences. Costs a small amount of
  API credit and is not run in CI.

The corpus intentionally includes near-miss distractors, an adjacent-topic
negative case, and a paraphrase case with no lexical overlap with its source
chunk (see ``questions.json`` notes) — these are designed to surface the
retrieval gap documented in the README (broad/paraphrased queries under-
retrieving), not to make the score look perfect.

The corpus logical names below must match the ``expected_sources`` values in
``questions.json``.
"""

import json
import shutil
import tempfile
import time
from pathlib import Path

from app.core import offline
from app.services import chunk_service, document_qa_service, document_service, rag_backends


QUESTIONS_PATH = Path(__file__).parent / "questions.json"
RESULTS_PATH = Path(__file__).parent / "results.md"

# Fixed evaluation corpus. Keys are logical names referenced by
# ``expected_sources`` in questions.json.
CORPUS = {
    "voyager": (
        "The Voyager spacecraft carries a golden record containing sounds and "
        "images from Earth, launched into interstellar space as a message to "
        "any civilization that might find it. It is powered by a "
        "radioisotope thermoelectric generator, a form of nuclear propulsion "
        "support that lets it keep transmitting decades after launch."
    ),
    "mars_rover": (
        "NASA's Perseverance rover explores the surface of Mars, drilling "
        "rock cores and searching for signs of ancient microbial life. It "
        "uses a plutonium-fueled radioisotope power system, a nuclear-based "
        "propulsion-support technology similar in principle to the one that "
        "powers the Voyager probes."
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
    """Run every question and compute aggregate quality metrics.

    ``retrieval_recall`` is computed per-question as the fraction of
    ``expected_sources`` that were actually cited, so multi-source questions
    (see the propulsion-technology case in questions.json) are graded
    proportionally rather than as a single pass/fail hit.
    """
    per_question = []
    answerable = 0
    citation_hits = 0
    fallback_total = 0
    fallback_correct = 0
    recall_sum = 0.0
    exact_hits = 0

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
            expected_ids = {
                name_to_id[name]
                for name in item.get("expected_sources", [])
                if name in name_to_id
            }
            retrieved_ids = set(result["sources"])
            found = expected_ids & retrieved_ids
            recall = len(found) / len(expected_ids) if expected_ids else 0.0
            exact_hit = expected_ids.issubset(retrieved_ids) and bool(expected_ids)

            keyword_hit = all(
                kw.lower() in result["answer"].lower()
                for kw in item.get("expected_keywords", [])
            )
            citation_present = len(result["sources"]) > 0

            recall_sum += recall
            exact_hits += int(exact_hit)
            citation_hits += int(citation_present)
            row["retrieval_recall"] = round(recall, 4)
            row["retrieval_hit"] = exact_hit
            row["keyword_hit"] = keyword_hit
            row["citation_present"] = citation_present
            row["passed"] = exact_hit and keyword_hit

        per_question.append(row)

    latencies = [r["latency_ms"] for r in per_question]
    metrics = {
        "embedding_backend": rag_backends.embedding_backend_name(),
        "llm_backend": "openai" if rag_backends.use_openai() else "none (extractive fallback)",
        "total_questions": len(questions),
        "answerable_questions": answerable,
        "fallback_questions": fallback_total,
        "retrieval_exact_hit_rate": round(exact_hits / answerable, 4) if answerable else 0.0,
        "retrieval_recall": round(recall_sum / answerable, 4) if answerable else 0.0,
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
        f"Backend: **{m['embedding_backend']} embeddings**, **{m['llm_backend']}** "
        "generation. Generated by `evals/run_eval.py`.",
        "",
        (
            "Local hashing-embedding retrieval (deterministic bag-of-words cosine "
            "similarity over Chroma, no LLM) plus an extractive answer — a fast, "
            "reproducible smoke test of the retrieval plumbing, not a measure of "
            "production answer quality. Run `make eval-live` with `OPENAI_API_KEY` "
            "set for a real accuracy measurement against OpenAI embeddings + chat "
            "generation."
            if m["embedding_backend"] == "local_hash"
            else (
                "Live run against the real OpenAI embedding + chat generation "
                "backend — this reflects production answer quality, not just "
                "retrieval plumbing. Not run in CI (costs API credit, "
                "non-deterministic)."
            )
        ),
        "",
        "The corpus includes near-miss distractors (two space-exploration docs),",
        "an adjacent-topic negative case, and a paraphrase case with no lexical",
        "overlap with its source chunk — see `evals/questions.json` for notes on",
        "what each is designed to catch.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Total questions | {m['total_questions']} |",
        f"| Answerable questions | {m['answerable_questions']} |",
        f"| Fallback questions | {m['fallback_questions']} |",
        f"| Retrieval exact-hit rate | {m['retrieval_exact_hit_rate']:.2%} |",
        f"| Retrieval recall (multi-source aware) | {m['retrieval_recall']:.2%} |",
        f"| Citation/source presence | {m['citation_presence_rate']:.2%} |",
        f"| Fallback accuracy | {m['fallback_accuracy']:.2%} |",
        f"| Avg latency (ms) | {m['avg_latency_ms']} |",
        f"| Max latency (ms) | {m['max_latency_ms']} |",
        "",
        "## Per-question results",
        "",
        "| Question | Type | Passed | Recall | Sources | Confidence | Latency (ms) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in results["per_question"]:
        source_count = len(r["sources"])
        recall = f"{r['retrieval_recall']:.0%}" if "retrieval_recall" in r else "-"
        lines.append(
            f"| {r['question']} | {r['type']} | {'yes' if r.get('passed') else 'no'} | "
            f"{recall} | {source_count} | {r['confidence_score']} | {r['latency_ms']} |"
        )
    lines.append("")
    return "\n".join(lines)


def run(
    questions_path: Path = QUESTIONS_PATH,
    results_path: Path | None = RESULTS_PATH,
    corpus: dict[str, str] | None = None,
    live: bool = False,
) -> dict:
    """Run the full eval against an isolated temp storage dir.

    Returns the results dict. If ``results_path`` is provided, also writes the
    markdown report there.

    ``live=False`` (default) pins offline mode: deterministic local hashing
    embeddings, no LLM, no network calls, safe for CI. ``live=True`` leaves
    the environment's real configuration in place, so with ``OPENAI_API_KEY``
    set it exercises the actual OpenAI-backed pipeline (costs API credit,
    not deterministic, not run in CI).
    """
    corpus = CORPUS if corpus is None else corpus
    questions = load_questions(questions_path)

    from app.services import vector_store

    tmp_dir = Path(tempfile.mkdtemp())
    original_storage = document_service.STORAGE_DIR
    original_offline = offline.is_offline()
    offline.set_offline(not live)
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
    import sys

    live = "--live" in sys.argv[1:]
    results_path = RESULTS_PATH.with_name("results_live.md") if live else RESULTS_PATH
    results = run(results_path=results_path, live=live)
    m = results["metrics"]
    print(f"DocuIntelAI RAG Evaluation ({m['embedding_backend']} / {m['llm_backend']})")
    print(f"  Retrieval exact-hit rate: {m['retrieval_exact_hit_rate']:.2%}")
    print(f"  Retrieval recall:        {m['retrieval_recall']:.2%}")
    print(f"  Citation/source presence: {m['citation_presence_rate']:.2%}")
    print(f"  Fallback accuracy:        {m['fallback_accuracy']:.2%}")
    print(f"  Avg latency (ms):         {m['avg_latency_ms']}")
    print(f"  Results written to:       {results_path}")


if __name__ == "__main__":
    main()
