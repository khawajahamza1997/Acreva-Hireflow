-- Acreva HireFlow — call intelligence (voice-note upload)
-- Run in Supabase SQL Editor (Dashboard → SQL → New query)

alter table public.candidates
  add column if not exists call_recording_path text default '',
  add column if not exists call_transcript text default '',
  add column if not exists salary_expectation text default '',
  add column if not exists notice_period text default '',
  add column if not exists availability text default '',
  add column if not exists flight_risk_notes text default '',
  add column if not exists call_consent boolean not null default false,
  add column if not exists call_recorded_at timestamptz;

-- ── Storage bucket for call recordings ──────────────────────
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'call-recordings',
  'call-recordings',
  false,
  26214400,
  array['audio/mpeg', 'audio/mp4', 'audio/x-m4a', 'audio/ogg', 'audio/wav', 'audio/webm']
)
on conflict (id) do nothing;

create policy "call_recordings_select" on storage.objects for select
  using (
    bucket_id = 'call-recordings'
    and (storage.foldername(name))[1] = public.user_organization_id()::text
  );

create policy "call_recordings_insert" on storage.objects for insert
  with check (
    bucket_id = 'call-recordings'
    and (storage.foldername(name))[1] = public.user_organization_id()::text
  );

create policy "call_recordings_delete" on storage.objects for delete
  using (
    bucket_id = 'call-recordings'
    and (storage.foldername(name))[1] = public.user_organization_id()::text
  );
