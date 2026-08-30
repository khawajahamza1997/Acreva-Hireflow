-- Acreva HireFlow — large-batch screening upgrade
-- Run in Supabase SQL Editor (Dashboard → SQL → New query)
-- Requires 002_call_intelligence.sql to have been applied first.

-- ── Processing batches (background CV upload / scoring runs) ──
create table if not exists public.processing_batches (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  job_id uuid references public.jobs(id) on delete set null,
  created_by uuid references public.profiles(id),
  status text not null default 'Uploading'
    check (status in ('Uploading', 'Queued', 'Processing', 'Completed', 'Completed with errors', 'Failed')),
  total_count integer not null default 0,
  completed_count integer not null default 0,
  failed_count integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_processing_batches_org on public.processing_batches(organization_id);

alter table public.processing_batches enable row level security;

create policy "processing_batches_all" on public.processing_batches for all
  using (organization_id = public.user_organization_id())
  with check (organization_id = public.user_organization_id());

drop trigger if exists processing_batches_updated_at on public.processing_batches;
create trigger processing_batches_updated_at
  before update on public.processing_batches
  for each row execute function public.set_updated_at();

-- ── Jobs: structured requirements + configurable scoring weights ──
alter table public.jobs
  add column if not exists structured_requirements jsonb not null default '{}',
  add column if not exists scoring_weights jsonb not null default
    '{"required_skills":35,"experience":25,"preferred_skills":15,"education":15,"certifications":5,"industry_experience":5}',
  add column if not exists requirements_source text not null default 'freeform'
    check (requirements_source in ('freeform', 'extracted', 'structured'));

-- ── Candidates: explainable scoring + processing state machine ──
alter table public.candidates
  add column if not exists location text default '',
  add column if not exists score_breakdown jsonb not null default '{}',
  add column if not exists requirement_results jsonb not null default '[]',
  add column if not exists strengths jsonb not null default '[]',
  add column if not exists concerns jsonb not null default '[]',
  add column if not exists meets_required boolean,
  add column if not exists employment_history jsonb not null default '[]',
  add column if not exists certifications jsonb not null default '[]',
  add column if not exists processing_status text not null default 'Completed'
    check (processing_status in ('Uploaded', 'Queued', 'Extracting', 'Analyzing', 'Scoring', 'Completed', 'Failed', 'Needs review')),
  add column if not exists processing_error text default '',
  add column if not exists processing_batch_id uuid references public.processing_batches(id) on delete set null;

create index if not exists idx_candidates_processing_batch on public.candidates(processing_batch_id);
create index if not exists idx_candidates_processing_status on public.candidates(processing_status);
