-- Run this FIRST in Supabase SQL Editor only if a previous migration attempt failed part-way.
-- Then run 001_initial.sql again.

drop trigger if exists candidates_updated_at on public.candidates;
drop function if exists public.set_updated_at() cascade;
drop function if exists public.user_organization_id() cascade;

drop table if exists public.email_templates cascade;
drop table if exists public.audit_logs cascade;
drop table if exists public.candidates cascade;
drop table if exists public.jobs cascade;
drop table if exists public.profiles cascade;
drop table if exists public.organizations cascade;

delete from storage.buckets where id = 'cvs';
