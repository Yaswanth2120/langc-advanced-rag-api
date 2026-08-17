# Phase 3: RAG Ingestion Pipeline

Goal:
Turn uploaded documents into searchable chunks and add document-grounded Q&A.

Requirements:
- Add chunking for uploaded document text.
- Store chunks locally under storage/chunks.json.
- Add chunk metadata:
  - chunk_id
  - document_id
  - chunk_index
  - text
  - created_at
- Add POST /documents/{document_id}/ingest
- Add GET /documents/{document_id}/chunks
- Add POST /query/documents
- /query/documents should:
  - accept question
  - retrieve relevant chunks using local keyword/BM25-style scoring for now
  - generate answer from retrieved chunks
  - return answer, sources, confidence_score
- If no relevant chunks exist, return:
  "I don't have enough information in the uploaded documents."

Constraints:
- Do not change existing /ask behavior.
- Do not replace current AdvancedRAGEngine.
- Do not add Chroma, Pinecone, or Qdrant yet.
- Do not add embeddings yet.
- Do not add database yet.
- Do not delete files.
- Keep this phase local and testable.
- Add tests for ingest, chunk listing, document query response, and no-context fallback.

Stop after Phase 3 is complete.