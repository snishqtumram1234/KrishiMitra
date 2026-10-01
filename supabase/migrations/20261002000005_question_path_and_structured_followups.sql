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
