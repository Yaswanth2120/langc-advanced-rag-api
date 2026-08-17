"""Shared lexical tokenization for the offline/local retrieval paths.

Used by ``LocalHashingEmbeddings`` (hashing embeddings) and
``AdvancedRAGEngine``'s keyword retrieval and quality-gate scoring. Kept in
one place so the stopword list and token rules can't drift between them.
"""

# Common English function words. Without filtering these, two unrelated
# documents can share enough "the"/"and"/"into"/"its"-style overlap to look
# lexically similar, producing false-positive retrieval hits (confirmed by
# evals/questions.json's adjacent-topic negative case before this fix).
STOPWORDS = {
    "the", "and", "for", "are", "was", "were", "its", "into", "that", "this",
    "with", "from", "have", "has", "had", "not", "but", "can", "all", "any",
    "who", "what", "when", "where", "why", "how", "which", "does", "did",
    "you", "your", "they", "their", "them", "his", "her", "our", "out",
    "about", "over", "under", "than", "then", "also", "such", "these",
    "those", "will", "would", "could", "should", "there", "here",
}


def tokenize(text: str) -> list[str]:
    """Lowercased, punctuation-stripped, stopword-filtered tokens (with repeats).

    Returns a list (not a set) so callers that weight by term frequency (e.g.
    the hashing embeddings) keep repeat occurrences; callers that only need
    set membership (e.g. keyword overlap scoring) can wrap with ``set(...)``.
    """
    tokens = []
    for raw in text.split():
        token = raw.strip(".,!?;:()[]{}\"'").lower()
        if len(token) > 2 and token not in STOPWORDS:
            tokens.append(token)
    return tokens
