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
