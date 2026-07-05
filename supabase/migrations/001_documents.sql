-- Document metadata table for LangC Advanced RAG API.
--
-- NOTE: this file reflects the ORIGINAL intended schema, not the current
-- live state. The live table drifted from it (it additionally has a nullable
-- text_path column); migration 003_align_schema.sql documents the live
-- reality and is AUTHORITATIVE for the final schema. Always apply the full
-- migration chain (001 -> 002 -> 003); never this file alone.
--
-- Provision a fresh Supabase project from this repo with:
--   supabase db push
-- (or run these files against the project's database in order). Do not
-- create the table by hand in the dashboard.

create table if not exists public.documents (
    document_id text primary key,
    filename    text not null,
    file_type   text not null,
    status      text not null,
    -- timestamptz to match the live table (see 003). The app writes
    -- timezone-aware ISO-8601 strings, which Postgres casts on insert.
    created_at  timestamptz not null
);

-- RLS is enabled and NO policies are created for anon/authenticated.
-- The FastAPI backend accesses this table exclusively with the service-role
-- key (SUPABASE_SERVICE_ROLE_KEY), which bypasses RLS by design. The anon/
-- publishable key — which is shipped client-side and is not a secret — has
-- zero access to this table.
alter table public.documents enable row level security;
