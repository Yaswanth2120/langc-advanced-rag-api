-- Align the committed schema with the LIVE documents table (authoritative).
--
-- The live table (verified via PostgREST introspection with the service-role
-- key) has:
--   document_id  text primary key
--   filename     text not null
--   file_type    text not null
--   status       text not null
--   created_at   timestamptz not null   -- NOT text as 001 originally declared
--   text_path    text null              -- historically stored the local text
--                                       -- extraction path for a document
--
-- This migration documents that reality and converges tables provisioned
-- from the original 001 to it. Every statement is a strict no-op on the
-- live table (column already exists / type already timestamptz), so applying
-- it never alters live data or takes a rewrite lock there.
--
-- text_path status: the application no longer reads or writes this column on
-- ANY backend — local file paths are derived from document_id
-- (app/services/document_service.py: stored_path_for / text_path_for). It is
-- retained, nullable and unpopulated, solely to match the live table.

-- Present on the live table; add for tables created by the original 001.
alter table public.documents add column if not exists text_path text;

-- Live created_at is already timestamptz. Convert only if a table still has
-- the original 001's text column, so this never touches the live table.
do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public'
          and table_name   = 'documents'
          and column_name  = 'created_at'
          and data_type    = 'text'
    ) then
        alter table public.documents
            alter column created_at type timestamptz
            using created_at::timestamptz;
    end if;
end $$;
