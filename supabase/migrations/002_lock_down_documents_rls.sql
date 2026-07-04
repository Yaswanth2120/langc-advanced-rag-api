-- SECURITY FIX: revoke anon/authenticated access to public.documents.
--
-- Migration 001 originally created a permissive policy ("documents_anon_all")
-- granting full read/write/delete to anyone holding the anon/publishable key.
-- That key ships client-side and is not a secret, so the policy allowed
-- bypassing the FastAPI auth layer entirely by hitting Supabase directly.
--
-- This migration removes it. With RLS enabled and no policies, anon and
-- authenticated roles have ZERO access; only the service-role key (which
-- bypasses RLS by design and is used server-side via
-- SUPABASE_SERVICE_ROLE_KEY) can touch this table.
--
-- ORDER MATTERS: configure the backend with SUPABASE_SERVICE_ROLE_KEY
-- BEFORE applying this migration, or document uploads/lists will start
-- failing (the backend's anon-key fallback loses access here).

drop policy if exists "documents_anon_all" on public.documents;

-- Idempotent: ensure RLS stays enabled (no policies remain for anon roles).
alter table public.documents enable row level security;
