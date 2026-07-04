"""Deterministic, offline embeddings used when no OpenAI key is configured.

This is the local fallback for the document-QA vector store. It hashes each
token into a fixed-width bag-of-words vector and L2-normalizes it, so cosine
similarity in Chroma approximates lexical overlap between a query and a chunk.

It makes no network calls, needs no model download, and is fully deterministic,
which keeps ingest, retrieval, and the test/eval suites reproducible offline.
The production path uses OpenAI embeddings instead (see ``rag_backends``).
"""

import hashlib
import math


class LocalHashingEmbeddings:
    """A langchain-compatible embeddings object (embed_documents/embed_query)."""

    def __init__(self, dim: int = 4096):
        self.dim = dim

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [
            token.strip(".,!?;:()[]{}\"'").lower()
            for token in text.split()
            if len(token.strip(".,!?;:()[]{}\"'")) > 2
        ]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in self._tokenize(text):
            index = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.dim
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
