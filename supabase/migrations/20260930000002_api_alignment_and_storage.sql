-- Align tables with the /api/cases endpoints and add the private image bucket.
--
-- routing_runs: one row per analysis (the whole orchestration of a case).
--   route   = the step sequence, e.g. "quality_gate>intent_router>vision>advisory>weather"
--   details = full result (message, follow-up, sources, route trace)
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
