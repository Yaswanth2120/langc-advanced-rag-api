import tempfile
from dataclasses import dataclass

from app.core.config import Settings
from app.core.text_utils import tokenize
from app.schemas.query import RetrievalMode
from app.services.rag_documents import DOCUMENTS
from app.services.rag_prompts import ANSWER_TEMPLATE, MULTI_QUERY_TEMPLATE, QUERY_REWRITE_TEMPLATE


@dataclass
class RAGResult:
    answer: str
    sources: list[str]
    mode: RetrievalMode
    rewritten_query: str | None
    retrieved_documents: int


class AdvancedRAGEngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._ready = False

    def _lazy_setup(self):
        if self._ready:
            return

        from langchain_chroma import Chroma
        from langchain_core.documents import Document
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        from app.services import rag_backends

        self.Document = Document
        self.StrOutputParser = StrOutputParser
        self.ChatPromptTemplate = ChatPromptTemplate

        # Same backend selection as document_qa_service: OpenAI when
        # configured, otherwise the deterministic offline fallback. This is
        # what makes /ask exercisable in CI without an API key — previously
        # this engine hardcoded OpenAI and had no offline path at all, so the
        # whole /ask pipeline (all four retrieval modes) went completely
        # untested outside of manual runs against a real key.
        self.llm = rag_backends.get_llm()
        self.embeddings = rag_backends.get_embeddings()

        source_docs = [
            Document(page_content=item["content"], metadata=item["metadata"])
            for item in DOCUMENTS
        ]
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        chunks = splitter.split_documents(source_docs)
        self.chunks = [self._contextualize_chunk(chunk) for chunk in chunks]

        self.vector_store = Chroma.from_documents(
            documents=self.chunks,
            embedding=self.embeddings,
            persist_directory=tempfile.mkdtemp(),
        )
        self.vector_retriever = self.vector_store.as_retriever(
            search_kwargs={"k": self.settings.top_k}
        )
        self.answer_prompt = ChatPromptTemplate.from_template(ANSWER_TEMPLATE)
        self.multi_query_prompt = ChatPromptTemplate.from_template(MULTI_QUERY_TEMPLATE)
        self.rewrite_prompt = ChatPromptTemplate.from_template(QUERY_REWRITE_TEMPLATE)
        self._ready = True

    def answer(self, question: str, mode: RetrievalMode) -> RAGResult:
        self._lazy_setup()

        docs, rewritten_query = self._retrieve(question, mode)
        context = self._format_docs(docs)

        if self.llm is None:
            # Offline fallback: no LLM available, return the retrieved
            # context verbatim (same extractive strategy as
            # document_qa_service when OPENAI_API_KEY is unset).
            answer = context or "I don't have enough information to answer that."
        else:
            answer_chain = self.answer_prompt | self.llm | self.StrOutputParser()
            answer = answer_chain.invoke({"context": context, "question": question})

        sources = sorted({doc.metadata.get("source", "unknown") for doc in docs})

        return RAGResult(
            answer=answer,
            sources=sources,
            mode=mode,
            rewritten_query=rewritten_query,
            retrieved_documents=len(docs),
        )

    def stream_answer(self, question: str, mode: RetrievalMode):
        """Yield ``{"type": ...}`` events: one ``meta``, then ``token``s, then ``done``.

        Mirrors ``document_qa_service.stream_answer_question``. Retrieval
        always runs eagerly (it's not itself streamed), so ``meta`` carries
        the final sources/mode/rewritten_query up front; only answer
        generation is streamed token-by-token when an LLM is configured.
        """
        self._lazy_setup()

        docs, rewritten_query = self._retrieve(question, mode)
        sources = sorted({doc.metadata.get("source", "unknown") for doc in docs})
        yield {
            "type": "meta",
            "mode": mode,
            "sources": sources,
            "rewritten_query": rewritten_query,
            "retrieved_documents": len(docs),
        }

        context = self._format_docs(docs)
        if self.llm is None:
            yield {"type": "token", "text": context or "I don't have enough information to answer that."}
            yield {"type": "done"}
            return

        answer_chain = self.answer_prompt | self.llm | self.StrOutputParser()
        for chunk in answer_chain.stream({"context": context, "question": question}):
            yield {"type": "token", "text": chunk}
        yield {"type": "done"}

    def _retrieve(self, question: str, mode: RetrievalMode):
        if mode == "basic":
            return self.vector_retriever.invoke(question), None
        if mode == "multi_query":
            return self._multi_query_retrieve(question), None
        if mode == "agentic":
            return self._agentic_retrieve(question)

        return self._hybrid_retrieve(question), None

    def _contextualize_chunk(self, chunk):
        source = chunk.metadata.get("source", "unknown")
        topic = chunk.metadata.get("topic", "general")
        return self.Document(
            page_content=f"Source: {source}. Topic: {topic}.\n\n{chunk.page_content}",
            metadata=chunk.metadata,
        )

    def _multi_query_retrieve(self, question: str):
        queries = [question]
        if self.llm is not None:
            # Query expansion needs an LLM; offline mode retrieves on the
            # original question only (still correct, just without the
            # recall boost from generated query variants).
            query_chain = self.multi_query_prompt | self.llm | self.StrOutputParser()
            generated = query_chain.invoke({"question": question})
            queries.extend(
                line.strip("- ").strip()
                for line in generated.splitlines()
                if line.strip()
            )

        docs = []
        for query in queries[:4]:
            docs.extend(self.vector_retriever.invoke(query))
        return self._dedupe_docs(docs)[: self.settings.top_k + 2]

    def _hybrid_retrieve(self, question: str):
        semantic_docs = self.vector_retriever.invoke(question)
        keyword_docs = self._keyword_retrieve(question, limit=self.settings.top_k)
        return self._dedupe_docs([*semantic_docs, *keyword_docs])[: self.settings.top_k + 2]

    def _agentic_retrieve(self, question: str):
        docs = self._hybrid_retrieve(question)
        if self.llm is None or self._top_relevance_score(question) >= self.settings.relevance_threshold:
            # Query rewriting needs an LLM; offline mode returns the hybrid
            # result as-is rather than pretending to retry.
            return docs, None

        rewrite_chain = self.rewrite_prompt | self.llm | self.StrOutputParser()
        rewritten_query = rewrite_chain.invoke({"question": question}).strip()
        retry_docs = self._hybrid_retrieve(rewritten_query)
        return self._dedupe_docs([*retry_docs, *docs])[: self.settings.top_k + 2], rewritten_query

    def _keyword_retrieve(self, question: str, limit: int):
        query_terms = set(tokenize(question))
        scored_docs = []
        for doc in self.chunks:
            doc_terms = set(tokenize(doc.page_content))
            score = len(query_terms.intersection(doc_terms))
            if score:
                scored_docs.append((score, doc))
        scored_docs.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored_docs[:limit]]

    def _top_relevance_score(self, question: str) -> float:
        """Best embedding-similarity score for ``question`` against the corpus.

        Used as the agentic-mode quality gate instead of lexical term-overlap
        counting: overlap counts don't scale across corpus sizes and can't
        tell a strong semantic match from a coincidental word match, whereas
        the vector store's own relevance score is the same signal
        ``document_qa_service`` already uses (via ``relevance_threshold``) to
        decide whether a retrieval is good enough to answer from.
        """
        results = self.vector_store.similarity_search_with_relevance_scores(
            question, k=self.settings.top_k
        )
        return max((score for _, score in results), default=0.0)

    @staticmethod
    def _format_docs(docs) -> str:
        return "\n\n".join(doc.page_content for doc in docs)

    @staticmethod
    def _dedupe_docs(docs):
        seen = set()
        unique_docs = []
        for doc in docs:
            key = (doc.page_content, doc.metadata.get("source"))
            if key not in seen:
                seen.add(key)
                unique_docs.append(doc)
        return unique_docs
