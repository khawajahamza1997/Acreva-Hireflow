-- Acreva HireFlow — security hardening, score-tier scheme, duplicate detection, usage tracking
-- Run in Supabase SQL Editor (Dashboard → SQL → New query)
-- Requires 002, 003, 004 to have been applied first.

-- ── Jobs: configurable score tier thresholds ────────────────
alter table public.jobs
  add column if not exists score_thresholds jsonb not null default '{"strong":90,"good":75,"potential":60}';

-- ── Candidates: duplicate-upload detection ──────────────────
alter table public.candidates
  add column if not exists file_hash text default '';

create index if not exists idx_candidates_org_hash on public.candidates(organization_id, file_hash);
create index if not exists idx_candidates_org_email on public.candidates(organization_id, email);

-- ── Usage tracking (billing-ready, not billing itself) ──────
create table if not exists public.usage_events (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  event_type text not null check (event_type in ('cv_uploaded', 'cv_analyzed', 'ai_call', 'email_sent')),
  quantity integer not null default 1,
  created_at timestamptz not null default now()
);

create index if not exists idx_usage_events_org on public.usage_events(organization_id);
create index if not exists idx_usage_events_org_type_created on public.usage_events(organization_id, event_type, created_at);

alter table public.usage_events enable row level security;

create policy "usage_events_all" on public.usage_events for all
  using (organization_id = public.user_organization_id())
  with check (organization_id = public.user_organization_id());
