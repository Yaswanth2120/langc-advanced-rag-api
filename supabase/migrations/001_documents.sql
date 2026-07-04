-- Document metadata table for LangC Advanced RAG API.
--
-- Columns match app/schemas/document.py (DocumentMetadata) exactly:
--   document_id, filename, file_type, status, created_at.
--
-- Provision a fresh Supabase project from this repo with:
--   supabase db push
-- (or run this file against the project's database). Do not create the
-- table by hand in the dashboard.

create table if not exists public.documents (
    document_id text primary key,
    filename    text not null,
    file_type   text not null,
    status      text not null,
    created_at  text not null
);

-- RLS is enabled and NO policies are created for anon/authenticated.
-- The FastAPI backend accesses this table exclusively with the service-role
-- key (SUPABASE_SERVICE_ROLE_KEY), which bypasses RLS by design. The anon/
-- publishable key — which is shipped client-side and is not a secret — has
-- zero access to this table.
alter table public.documents enable row level security;
