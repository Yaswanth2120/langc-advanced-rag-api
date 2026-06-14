KNOWLEDGE_BASE = """# LangC Advanced RAG System

LangC is a deployable RAG API built with FastAPI, LangChain, OpenAI embeddings,
Chroma vector search, LangSmith tracing, and optional Supabase integration.

The API supports four retrieval modes:

1. Basic RAG uses vector similarity search.
2. Multi-query RAG creates multiple search queries to improve recall.
3. Hybrid RAG combines semantic vector search with keyword search.
4. Agentic RAG retrieves, evaluates, rewrites weak queries, and retries.

LangChain is used for prompts, model calls, output parsing, and RAG composition.
LangGraph examples are included to show how agentic workflows can be expanded
into stateful graphs with retries, routing, persistence, and human-in-the-loop.

Vector stores save embeddings so the app can search by meaning instead of only
matching exact words. Chroma is used as the local vector store for deployment
simplicity.

LangSmith is used for tracing, debugging, monitoring, and evaluating LLM calls.
Supabase is optional and can be used later for user data, documents, metadata,
or persistent conversation history.
"""


ADVANCED_RAG_NOTES = """# Advanced RAG Features

Contextual retrieval:
Each chunk is embedded with source and topic context. This reduces context loss
when chunks contain pronouns, vague references, or incomplete sections.

Multi-query retrieval:
The model rewrites the user question into multiple search queries. This helps
when the user asks a vague question or uses different wording than the docs.

Hybrid retrieval:
The system combines semantic vector retrieval with keyword retrieval. This is
useful for exact terms like library names, commands, file names, model names,
technical acronyms, or version numbers.

Agentic RAG:
The system first retrieves documents, checks if the result looks strong enough,
rewrites the question when retrieval is weak, and tries again before answering.

Late chunking:
The full native late-chunking technique requires token-level embedding support.
This project uses a practical production-friendly version by adding context to
chunks before embedding.

GraphRAG:
GraphRAG is useful when answers require relationships between entities. The repo
keeps GraphRAG examples under examples/advanced_rag for future expansion.

Multimodal RAG:
Multimodal RAG retrieves across text and media such as PDFs, images, charts, or
screenshots. The repo keeps multimodal examples under examples/advanced_rag.
"""


DOCUMENTS = [
    {
        "content": KNOWLEDGE_BASE,
        "metadata": {"source": "langc_system_overview", "topic": "production_rag"},
    },
    {
        "content": ADVANCED_RAG_NOTES,
        "metadata": {"source": "advanced_rag_notes", "topic": "advanced_rag"},
    },
]
