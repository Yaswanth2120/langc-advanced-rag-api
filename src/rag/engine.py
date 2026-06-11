import tempfile
from dataclasses import dataclass

from src.config import Settings
from src.rag.documents import DOCUMENTS
from src.rag.prompts import ANSWER_TEMPLATE, MULTI_QUERY_TEMPLATE, QUERY_REWRITE_TEMPLATE
from src.schemas import RetrievalMode


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

        from langchain.chat_models import init_chat_model
        from langchain_chroma import Chroma
        from langchain_core.documents import Document
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import OpenAIEmbeddings
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        self.Document = Document
        self.StrOutputParser = StrOutputParser
        self.ChatPromptTemplate = ChatPromptTemplate

        self.llm = init_chat_model(
            model=self.settings.chat_model,
            temperature=self.settings.temperature,
        )
        self.embeddings = OpenAIEmbeddings(model=self.settings.embedding_model)

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
        query_chain = self.multi_query_prompt | self.llm | self.StrOutputParser()
        generated = query_chain.invoke({"question": question})
        queries = [question]
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
        if self._retrieval_quality(question, docs) >= 2:
            return docs, None

        rewrite_chain = self.rewrite_prompt | self.llm | self.StrOutputParser()
        rewritten_query = rewrite_chain.invoke({"question": question}).strip()
        retry_docs = self._hybrid_retrieve(rewritten_query)
        return self._dedupe_docs([*retry_docs, *docs])[: self.settings.top_k + 2], rewritten_query

    def _keyword_retrieve(self, question: str, limit: int):
        query_terms = self._tokenize(question)
        scored_docs = []
        for doc in self.chunks:
            doc_terms = self._tokenize(doc.page_content)
            score = len(query_terms.intersection(doc_terms))
            if score:
                scored_docs.append((score, doc))
        scored_docs.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored_docs[:limit]]

    def _retrieval_quality(self, question: str, docs) -> int:
        query_terms = self._tokenize(question)
        matched_terms = set()
        for doc in docs:
            matched_terms.update(query_terms.intersection(self._tokenize(doc.page_content)))
        return len(matched_terms)

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

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {
            token.strip(".,!?;:()[]{}\"'").lower()
            for token in text.split()
            if len(token.strip(".,!?;:()[]{}\"'")) > 2
        }
