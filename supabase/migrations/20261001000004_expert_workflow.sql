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
