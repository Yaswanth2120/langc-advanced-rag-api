# Phase 2: Document Upload

Goal:
Add real document upload support for DocuIntelAI.

Requirements:
- Add POST /documents/upload
- Add GET /documents
- Accept .txt, .md, .pdf files
- Reject unsupported file types
- Save uploaded files locally under storage/uploads/
- Extract text from uploaded documents
- Store document metadata in local JSON file or lightweight local storage for now
- Return document_id, filename, file_type, status, created_at
- Add tests for:
  - successful TXT upload
  - unsupported file type rejection
  - GET /documents returns uploaded metadata

Constraints:
- Do not modify existing /ask behavior
- Do not delete existing routes
- Do not add database dependency yet
- Do not implement embeddings yet
- Do not implement vector search yet
- Do not replace FastAPI
- Ask before deleting files

Stop after Phase 2 is complete.