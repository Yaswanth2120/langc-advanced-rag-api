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

-- The app authenticates to PostgREST with the project's anon/publishable key,
-- so row-level security must permit that role to read and write this table.
alter table public.documents enable row level security;

drop policy if exists "documents_anon_all" on public.documents;
create policy "documents_anon_all"
    on public.documents
    for all
    to anon, authenticated
    using (true)
    with check (true);
