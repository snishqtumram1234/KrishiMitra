-- ============================================================ 20260930000001_core_case_tables.sql
-- Core case + orchestration logging tables.
-- Writes to routing_runs / model_runs are done by the backend (service role, bypasses RLS).

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------- enums
create type decision_state as enum (
  'NEEDS_BETTER_IMAGE',
  'NEEDS_MORE_CONTEXT',
  'PRELIMINARY_GUIDANCE',
  'EXPERT_REVIEW',
  'UNSUPPORTED'
);

create type image_kind as enum ('close_up_leaf', 'field_overview');

-- ---------------------------------------------------------------- shared trigger
create or replace function set_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------- crop_cases
create table crop_cases (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid references auth.users (id) on delete set null,
  crop             text not null,
  district         text not null default 'Pune',
  state            text not null default 'Maharashtra',
  symptom_context  text not null,
  language         text not null default 'en' check (language in ('en', 'mr')),
  growth_stage     text,
  recent_rainfall  text,
  description      text,
  decision_state   decision_state,          -- null until the orchestrator decides
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create index crop_cases_user_id_idx on crop_cases (user_id);
create index crop_cases_created_at_idx on crop_cases (created_at desc);

create trigger crop_cases_set_updated_at
  before update on crop_cases
  for each row execute function set_updated_at();

-- ---------------------------------------------------------------- case_images
create table case_images (
  id               uuid primary key default gen_random_uuid(),
  case_id          uuid not null references crop_cases (id) on delete cascade,
  kind             image_kind not null,
  storage_path     text not null,           -- Supabase Storage object path
  content_type     text,
  size_bytes       integer check (size_bytes is null or size_bytes >= 0),
  quality_score    real check (quality_score is null or quality_score between 0 and 1),
  quality_passed   boolean,                 -- null until the quality gate runs
  quality_details  jsonb,
  created_at       timestamptz not null default now()
);

create index case_images_case_id_idx on case_images (case_id);

-- ---------------------------------------------------------------- routing_runs
-- One row per orchestrator decision for a case.
create table routing_runs (
  id               uuid primary key default gen_random_uuid(),
  case_id          uuid not null references crop_cases (id) on delete cascade,
  route            text not null,           -- e.g. quality_gate, classify, retrieve, escalate
  intent           text,
  decision_state   decision_state,
  confidence       real check (confidence is null or confidence between 0 and 1),
  reason           text,
  latency_ms       integer check (latency_ms is null or latency_ms >= 0),
  cost_usd         numeric(12, 6) not null default 0 check (cost_usd >= 0),
  outcome          text,
  details          jsonb,
  created_at       timestamptz not null default now()
);

create index routing_runs_case_id_idx on routing_runs (case_id);
create index routing_runs_created_at_idx on routing_runs (created_at desc);

-- ---------------------------------------------------------------- model_runs
-- One row per model/tool call made by the orchestrator.
create table model_runs (
  id               uuid primary key default gen_random_uuid(),
  routing_run_id   uuid not null references routing_runs (id) on delete cascade,
  case_id          uuid not null references crop_cases (id) on delete cascade,
  image_id         uuid references case_images (id) on delete set null,
  model_name       text not null,
  model_version    text,
  input_summary    jsonb,
  output           jsonb,                   -- e.g. class probabilities
  predicted_label  text,
  confidence       real check (confidence is null or confidence between 0 and 1),
  latency_ms       integer check (latency_ms is null or latency_ms >= 0),
  cost_usd         numeric(12, 6) not null default 0 check (cost_usd >= 0),
  outcome          text not null default 'ok',   -- ok | error | timeout
  error            text,
  created_at       timestamptz not null default now()
);

create index model_runs_routing_run_id_idx on model_runs (routing_run_id);
create index model_runs_case_id_idx on model_runs (case_id);

-- ---------------------------------------------------------------- RLS
alter table crop_cases   enable row level security;
alter table case_images  enable row level security;
alter table routing_runs enable row level security;
alter table model_runs   enable row level security;

-- Farmers manage their own cases and images.
create policy crop_cases_owner on crop_cases
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy case_images_owner on case_images
  for all to authenticated
  using (exists (select 1 from crop_cases c where c.id = case_id and c.user_id = auth.uid()))
  with check (exists (select 1 from crop_cases c where c.id = case_id and c.user_id = auth.uid()));

-- Farmers may read (never write) the logs for their own cases.
create policy routing_runs_owner_read on routing_runs
  for select to authenticated
  using (exists (select 1 from crop_cases c where c.id = case_id and c.user_id = auth.uid()));

create policy model_runs_owner_read on model_runs
  for select to authenticated
  using (exists (select 1 from crop_cases c where c.id = case_id and c.user_id = auth.uid()));


-- ============================================================ 20260930000002_api_alignment_and_storage.sql
-- Align tables with the /api/cases endpoints and add the private image bucket.
--
-- routing_runs: one row per analysis (the whole orchestration of a case).
--   route   = orchestration path chosen by intent: image_diagnosis | weather | treatment_safety |
--             advisory_lookup | general_crop_question | expert_escalation | unsupported_request
--   intent  = intent from the keyword router
--   details = steps called, intent rule/confidence, full result (message, sources, route trace)
-- model_runs: one row per model/tool call inside that analysis; `step` names the call.

alter type image_kind rename value 'close_up_leaf' to 'leaf_closeup';

alter table crop_cases add column symptom_started_at date;

alter table model_runs add column step text;

create index routing_runs_case_created_idx on routing_runs (case_id, created_at desc);

-- ---------------------------------------------------------------- storage
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('case-images', 'case-images', false, 10485760, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do nothing;

-- Objects are stored as <user_id>/<case_id>/<file>. The backend writes with the service role;
-- a signed-in farmer may read only files under their own user_id folder.
create policy case_images_bucket_owner_read on storage.objects
  for select to authenticated
  using (bucket_id = 'case-images' and (storage.foldername(name))[1] = auth.uid()::text);


-- ============================================================ 20261001000003_weather_snapshots.sql
-- Every weather result the backend produces, whatever its source.
--   source      = live (Open-Meteo, NOT IMD) | cached (a re-served live row) | demo | unavailable
--   observed_at = the time the data describes; fetched_at = when we produced this result
--   error       = why the live source was not used (null when source = live)
-- Cached fallbacks read the latest source = 'live' row for the district.

create table weather_snapshots (
  id                        uuid primary key default gen_random_uuid(),
  district                  text not null,
  source                    text not null check (source in ('live', 'cached', 'demo', 'unavailable')),
  provider                  text,
  observed_at               timestamptz,
  fetched_at                timestamptz not null,
  stale                     boolean not null default false,
  temperature_c             real,
  humidity_pct              real,
  precipitation_mm          real,
  rain_next_24h_mm          real,
  rain_probability_max_pct  real,
  wind_speed_kmh            real,
  error                     text,
  created_at                timestamptz not null default now()
);

create index weather_snapshots_live_lookup_idx
  on weather_snapshots (district, observed_at desc) where source = 'live';

alter table weather_snapshots enable row level security;

-- District weather is not personal data; any signed-in user may read it. Writes: backend only.
create policy weather_snapshots_read on weather_snapshots
  for select to authenticated using (true);


-- ============================================================ 20261001000004_expert_workflow.sql
-- Expert workflow: escalations + reviews, farmer follow-ups, audit trail.
-- The backend writes all of these with the service role. Experts are identified by
-- auth.users.raw_app_meta_data->>'role' = 'expert' (set server-side, never by the user).

-- One row per escalation. Lifecycle:
--   pending_review -> reviewed (likely | insufficient | unknown)
--   pending_review -> awaiting_farmer (request_more) -> follow_up_received (farmer answered)
create table expert_reviews (
  id                    uuid primary key default gen_random_uuid(),
  case_id               uuid not null references crop_cases (id) on delete cascade,
  routing_run_id        uuid not null references routing_runs (id) on delete cascade,
  status                text not null check (status in ('pending_review', 'awaiting_farmer', 'reviewed', 'follow_up_received')),
  escalation_reason     text not null,
  snapshot              jsonb not null,  -- images, predictions, missing info, sources, question
  decision              text check (decision in ('likely', 'insufficient', 'request_more', 'unknown')),
  label                 text check (label in ('healthy', 'rust_like', 'leaf_spot_like', 'insect_damage', 'unknown')),
  notes                 text,
  recommended_advisory  jsonb,
  reviewer_id           uuid references auth.users (id) on delete set null,
  reviewed_at           timestamptz,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  check (decision is not null or status = 'pending_review' or status = 'follow_up_received'),
  check (label is null or decision = 'likely')
);

create index expert_reviews_status_idx on expert_reviews (status, created_at desc);
create index expert_reviews_case_idx on expert_reviews (case_id, created_at desc);

create trigger expert_reviews_set_updated_at
  before update on expert_reviews
  for each row execute function set_updated_at();

create table case_follow_ups (
  id          uuid primary key default gen_random_uuid(),
  case_id     uuid not null references crop_cases (id) on delete cascade,
  answer      text,
  image_id    uuid references case_images (id) on delete set null,
  created_at  timestamptz not null default now(),
  check (answer is not null or image_id is not null)
);

create index case_follow_ups_case_idx on case_follow_ups (case_id, created_at);

-- Append-only audit trail: escalation_created | escalation_updated | expert_review_submitted | follow_up_submitted
create table audit_events (
  id                uuid primary key default gen_random_uuid(),
  event_type        text not null,
  actor_id          uuid references auth.users (id) on delete set null,  -- null = system
  actor_role        text not null check (actor_role in ('system', 'farmer', 'expert')),
  case_id           uuid references crop_cases (id) on delete set null,
  expert_review_id  uuid references expert_reviews (id) on delete set null,
  details           jsonb not null default '{}'::jsonb,
  created_at        timestamptz not null default now()
);

create index audit_events_case_idx on audit_events (case_id, created_at);

-- Audit rows are never changed or removed.
create or replace function audit_events_immutable() returns trigger
language plpgsql as $$
begin
  raise exception 'audit_events is append-only';
end;
$$;

create trigger audit_events_no_update
  before update or delete on audit_events
  for each row execute function audit_events_immutable();

-- ---------------------------------------------------------------- RLS
alter table expert_reviews  enable row level security;
alter table case_follow_ups enable row level security;
alter table audit_events    enable row level security;  -- no policies: backend (service role) only

-- Farmers may read the expert side of their own cases and their own follow-ups.
create policy expert_reviews_owner_read on expert_reviews
  for select to authenticated
  using (exists (select 1 from crop_cases c where c.id = case_id and c.user_id = auth.uid()));

create policy case_follow_ups_owner_read on case_follow_ups
  for select to authenticated
  using (exists (select 1 from crop_cases c where c.id = case_id and c.user_id = auth.uid()));


-- ============================================================ 20261002000005_question_path_and_structured_followups.sql
-- Question path, structured follow-up answers.
--
-- crop_cases.entry_point: how the case was created.
--   crop_check = the photo form (POST /api/cases)
--   question   = the no-photo "ask a question" path (POST /api/questions)
--
-- case_follow_ups.question_id / option: a structured answer to a follow-up question the API asked
-- (see follow_up_options in the analysis response). `answer` still holds the readable text.
--
-- Advisory sources live inside routing_runs.details and expert_reviews.snapshot (jsonb). They now carry
-- source_type ('demo' | 'ingested'), published_at, source_url and retrieved_at. Only an ingested
-- advisory document may have verified = true; the API enforces that when it builds a source.

alter table crop_cases
  add column entry_point text not null default 'crop_check'
  check (entry_point in ('crop_check', 'question'));

alter table case_follow_ups
  add column question_id text,
  add column option text,
  add constraint case_follow_ups_option_needs_question check (option is null or question_id is not null);


