-- Acreva HireFlow — comparison, Ask HireFlow, bulk ops, versioning, email log
-- Run in Supabase SQL Editor (Dashboard → SQL → New query)
-- Requires 002_call_intelligence.sql and 003_screening_upgrade.sql to have been applied first.

-- ── Job requirement versioning ──────────────────────────────
alter table public.jobs
  add column if not exists requirements_version integer not null default 1;

create table if not exists public.job_requirement_versions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  job_id uuid not null references public.jobs(id) on delete cascade,
  version integer not null,
  description text not null default '',
  structured_requirements jsonb not null default '{}',
  scoring_weights jsonb not null default '{}',
  created_by uuid references public.profiles(id),
  created_at timestamptz not null default now()
);

create index if not exists idx_job_requirement_versions_job on public.job_requirement_versions(job_id);

alter table public.job_requirement_versions enable row level security;

create policy "job_requirement_versions_all" on public.job_requirement_versions for all
  using (organization_id = public.user_organization_id())
  with check (organization_id = public.user_organization_id());

-- ── Candidates: which requirements version produced the current score ──
alter table public.candidates
  add column if not exists scored_requirements_version integer;

-- ── Email send log ───────────────────────────────────────────
create table if not exists public.email_logs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  candidate_id uuid references public.candidates(id) on delete set null,
  job_id uuid references public.jobs(id) on delete set null,
  template_type text default '',
  subject text default '',
  to_email text default '',
  status text not null check (status in ('sent', 'failed')),
  error text default '',
  sent_by uuid references public.profiles(id),
  created_at timestamptz not null default now()
);

create index if not exists idx_email_logs_org on public.email_logs(organization_id);
create index if not exists idx_email_logs_candidate on public.email_logs(candidate_id);
create index if not exists idx_email_logs_job on public.email_logs(job_id);

alter table public.email_logs enable row level security;

create policy "email_logs_all" on public.email_logs for all
  using (organization_id = public.user_organization_id())
  with check (organization_id = public.user_organization_id());
