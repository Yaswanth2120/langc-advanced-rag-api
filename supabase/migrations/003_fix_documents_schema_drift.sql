-- Fix schema drift between migration 001 and tables provisioned before it.
--
-- Live tables created by hand (pre-001) drifted from the committed schema:
--   1. A stray `text_path` column exists. It is dead: since the Phase-6
--      field-mismatch fix the app derives all local file paths from
--      document_id (document_service.stored_path_for / text_path_for) and
--      never reads or writes this column. Drop it.
--   2. `created_at` is timestamptz on the live table, while 001 declared
--      text. timestamptz is the correct type and is what 001 now declares;
--      convert any text column to it. The app writes timezone-aware
--      ISO-8601 strings, which Postgres casts to timestamptz natively, and
--      PostgREST serializes back to ISO-8601 strings — so no application
--      code change is required.
--
-- Both statements are no-ops on a table already in the target state.

alter table public.documents drop column if exists text_path;

alter table public.documents
    alter column created_at type timestamptz
    using created_at::timestamptz;
