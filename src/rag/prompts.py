ANSWER_TEMPLATE = """You are a senior RAG system answering with retrieved context.

Rules:
- Use only the context below.
- If the answer is not in the context, say you do not know.
- Be concise, practical, and specific.
- Mention relevant source names when helpful.

Context:
{context}

Question: {question}

Answer:"""


MULTI_QUERY_TEMPLATE = """Create three short search queries for this user question.
Return one query per line.
Do not number the queries.

Question: {question}"""


QUERY_REWRITE_TEMPLATE = """Rewrite this user question for better document retrieval.
Make it specific and searchable.
Return only the rewritten query.

Original question: {question}"""
