-- Acreva HireFlow — initial schema
-- Run in Supabase SQL Editor (Dashboard → SQL → New query)

create extension if not exists "pgcrypto";

-- ── Organizations ───────────────────────────────────────────
create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text unique not null,
  stripe_customer_id text,
  stripe_subscription_id text,
  subscription_status text not null default 'trialing'
    check (subscription_status in ('trialing', 'active', 'past_due', 'canceled', 'incomplete')),
  trial_ends_at timestamptz not null default (now() + interval '14 days'),
  plan text not null default 'starter',
  created_at timestamptz not null default now()
);

-- ── Profiles (linked to Supabase auth.users) ────────────────
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  organization_id uuid not null references public.organizations(id) on delete cascade,
  email text not null,
  full_name text default '',
  "role" text not null default 'recruiter'
    check ("role" in ('owner', 'recruiter', 'viewer')),
  created_at timestamptz not null default now()
);

create index if not exists idx_profiles_org on public.profiles(organization_id);

-- ── Jobs ────────────────────────────────────────────────────
create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  title text not null,
  description text not null default '',
  created_by uuid references public.profiles(id),
  created_at timestamptz not null default now()
);

create index if not exists idx_jobs_org on public.jobs(organization_id);

-- ── Candidates ──────────────────────────────────────────────
create table if not exists public.candidates (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  job_id uuid references public.jobs(id) on delete set null,
  name text not null default 'Unknown',
  email text default '',
  phone text default '',
  "current_role" text default '',
  skills text default '',
  experience_years numeric default 0,
  education text default '',
  filename text default '',
  cv_storage_path text default '',
  cv_text text default '',
  score numeric,
  score_status text,
  score_reason text,
  shortlisted boolean not null default false,
  contacted boolean not null default false,
  interview_date text default '',
  interview_time text default '',
  interview_stage text default '',
  status text not null default 'New Applicant',
  notes text default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_candidates_org on public.candidates(organization_id);
create index if not exists idx_candidates_job on public.candidates(job_id);
create index if not exists idx_candidates_status on public.candidates(status);

-- ── Audit log ───────────────────────────────────────────────
create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid references public.profiles(id),
  user_email text default '',
  action text not null,
  entity_type text not null,
  entity_id uuid,
  details jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create index if not exists idx_audit_org on public.audit_logs(organization_id);
create index if not exists idx_audit_created on public.audit_logs(created_at desc);

-- ── Email templates (per org, editable) ─────────────────────
create table if not exists public.email_templates (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  template_type text not null
    check (template_type in ('interview_invite', 'follow_up', 'acknowledgement')),
  subject text not null,
  body text not null,
  updated_at timestamptz not null default now(),
  unique (organization_id, template_type)
);

-- ── Row Level Security ──────────────────────────────────────
alter table public.organizations enable row level security;
alter table public.profiles enable row level security;
alter table public.jobs enable row level security;
alter table public.candidates enable row level security;
alter table public.audit_logs enable row level security;
alter table public.email_templates enable row level security;

create or replace function public.user_organization_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
  select organization_id from public.profiles where id = auth.uid()
$$;

-- Organizations: members can read their org
create policy "org_select" on public.organizations for select
  using (id = public.user_organization_id());

create policy "org_update_owner" on public.organizations for update
  using (
    id = public.user_organization_id()
    and exists (
      select 1 from public.profiles p
      where p.id = auth.uid() and p."role" = 'owner'
    )
  );

-- Profiles
create policy "profiles_select" on public.profiles for select
  using (organization_id = public.user_organization_id());

create policy "profiles_update_self" on public.profiles for update
  using (id = auth.uid());

-- Jobs
create policy "jobs_all" on public.jobs for all
  using (organization_id = public.user_organization_id())
  with check (organization_id = public.user_organization_id());

-- Candidates
create policy "candidates_all" on public.candidates for all
  using (organization_id = public.user_organization_id())
  with check (organization_id = public.user_organization_id());

-- Audit logs (read only for org members; insert via service role from API)
create policy "audit_select" on public.audit_logs for select
  using (organization_id = public.user_organization_id());

-- Email templates
create policy "templates_all" on public.email_templates for all
  using (organization_id = public.user_organization_id())
  with check (organization_id = public.user_organization_id());

-- ── Storage bucket for CV files ─────────────────────────────
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'cvs',
  'cvs',
  false,
  10485760,
  array['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
)
on conflict (id) do nothing;

create policy "cvs_select" on storage.objects for select
  using (
    bucket_id = 'cvs'
    and (storage.foldername(name))[1] = public.user_organization_id()::text
  );

create policy "cvs_insert" on storage.objects for insert
  with check (
    bucket_id = 'cvs'
    and (storage.foldername(name))[1] = public.user_organization_id()::text
  );

create policy "cvs_delete" on storage.objects for delete
  using (
    bucket_id = 'cvs'
    and (storage.foldername(name))[1] = public.user_organization_id()::text
  );

-- ── Updated_at trigger ──────────────────────────────────────
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists candidates_updated_at on public.candidates;
create trigger candidates_updated_at
  before update on public.candidates
  for each row execute function public.set_updated_at();
