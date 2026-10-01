/**
 * Types for the KrishiMitra backend, taken from the generated OpenAPI schema (api-schema.d.ts; regenerate with
 * `npm run api:types`) plus the code lists the API documents but types as plain strings (API.md).
 *
 * Each `*_CODES` array lists every value a structured field can take. They exist so the i18n layer can prove it has
 * copy for every code. `Expect<Equal<...>>` makes the compiler fail if an array and the generated type disagree.
 */
import type { components } from "./api-schema";

type S = components["schemas"];

// ---------------------------------------------------------------- compile-time helpers
type Equal<A, B> = (<T>() => T extends A ? 1 : 2) extends <T>() => T extends B ? 1 : 2 ? true : false;
type Expect<T extends true> = T;

// ---------------------------------------------------------------- generated, aliased
export type DecisionState = S["DecisionState"];
export type ReasonCode = S["ReasonCode"];
export type Category = S["Category"];
export type Intent = S["Intent"];
export type ImageKind = S["ImageKind"];
export type ExpertStatus = S["ExpertStatus"];
export type ReviewDecision = S["ReviewDecision"];
export type ConfidenceBand = NonNullable<S["OrchestratorResult"]["confidence_band"]>;
export type TraceStatus = S["TraceStep"]["status"];
export type WeatherSource = NonNullable<S["WeatherResult"]["source"]>;
export type SourceType = NonNullable<S["AdvisorySource"]["source_type"]>;
export type FollowUpAnswerType = S["FollowUpOptions"]["answer_type"];

export type CaseCreate = S["CaseCreate"];
export type CaseOut = S["CaseOut"];
export type ImageOut = S["ImageOut"];
export type QuestionCreate = S["QuestionCreate"];
export type SignedUrlOut = S["SignedUrlOut"];
export type CaseAnalysisOut = S["CaseAnalysisOut"];
export type OrchestratorResult = S["OrchestratorResult"];
export type TraceStep = S["TraceStep"];
export type FollowUpOptions = S["FollowUpOptions"];
export type AdvisorySource = S["AdvisorySource"];
export type ExpertFeedback = S["ExpertFeedback"];
export type RunTrace = S["RunTrace"];
export type WeatherResult = S["WeatherResult"];
export type ExpertCaseSummary = S["ExpertCaseSummary"];
export type ExpertCaseDetail = S["ExpertCaseDetail"];
export type ExpertReviewRecord = S["ExpertReviewRecord"];
export type ReviewIn = S["ReviewIn"];
export type Overview = S["Overview"];
export type RoutesOut = S["RoutesOut"];
export type CostLatencyOut = S["CostLatencyOut"];

// ---------------------------------------------------------------- code lists (generated enums)
export const DECISION_STATES = [
  "NEEDS_BETTER_IMAGE",
  "NEEDS_MORE_CONTEXT",
  "PRELIMINARY_GUIDANCE",
  "EXPERT_REVIEW",
  "UNSUPPORTED",
] as const;
export const REASON_CODES = [
  "quality_failed",
  "crop_not_soybean",
  "farmer_requested_expert",
  "unsupported_request",
  "intent_unclear",
  "treatment_needs_expert",
  "treatment_verified_source",
  "weather_context",
  "advisory_lookup",
  "general_crop_question",
  "low_confidence_request_evidence",
  "low_confidence_escalate",
  "models_conflict",
  "label_unknown",
  "mid_confidence",
  "high_confidence",
  "sources_unavailable",
] as const;
export const CATEGORIES = ["healthy", "rust_like", "leaf_spot_like", "insect_damage", "unknown"] as const;
export const CONFIDENCE_BANDS = ["low", "medium", "high"] as const;
export const TRACE_STATUSES = ["completed", "failed", "skipped"] as const;
export const WEATHER_SOURCES = ["live", "cached", "demo", "unavailable"] as const;
export const SOURCE_TYPES = ["demo", "ingested"] as const;
export const EXPERT_STATUSES = ["pending_review", "awaiting_farmer", "reviewed", "follow_up_received"] as const;
export const REVIEW_DECISIONS = ["likely", "insufficient", "request_more", "unknown"] as const;
export const IMAGE_KINDS = ["leaf_closeup", "field_overview"] as const;
export const FOLLOW_UP_ANSWER_TYPES = ["choice", "photo", "text"] as const;

// ---------------------------------------------------------------- code lists the API documents as plain strings (API.md)
/** `reason_detail` when `reason_code` is quality_failed: the first quality-gate issue. */
export const QUALITY_ISSUES = [
  "missing_image",
  "unreadable_image",
  "too_small",
  "too_dark",
  "too_bright",
  "blurry",
  "no_leaf_detected",
] as const;
/** `calls[].output.next_action` of the quality gate. */
export const QUALITY_NEXT_ACTIONS = [
  "continue",
  "upload_image",
  "retake_closer",
  "retake_in_daylight",
  "retake_avoid_glare",
  "retake_steady",
  "retake_leaf_in_frame",
] as const;
/** `reason_detail` when `reason_code` is sources_unavailable. */
export const SOURCE_FAILURES = [
  "advisory",
  "weather",
  "vision_error",
  "quality_gate_error",
  "intent_router_error",
] as const;
export const MISSING_INFORMATION_CODES = [
  "close_up_photo",
  "clearer_close_up_photo",
  "symptom_description",
  "affected_leaf_position",
  "verified_advisory_source",
  "current_weather",
  "treatment_source",
  "field_overview_photo",
  "growth_stage",
  "symptom_start_date",
  "recent_rainfall",
] as const;
export const FOLLOW_UP_QUESTION_IDS = ["leaf_position", "field_overview_photo", "describe_problem"] as const;
export const FOLLOW_UP_OPTION_CODES = ["older_leaves", "younger_leaves", "both"] as const;
export const TRACE_STEP_IDS = [
  "intent_router",
  "quality_gate",
  "vision",
  "advisory",
  "weather",
  "policy_decision",
] as const;
export const SKIPPED_REASONS = ["route_does_not_use_step", "stopped_earlier", "confidence_not_high"] as const;
/** `result.path` / `RunTrace.path`. "none" is stored only for a non-soybean crop. */
export const ROUTE_PATHS = [
  "image_diagnosis",
  "weather",
  "treatment_safety",
  "advisory_lookup",
  "general_crop_question",
  "expert_escalation",
  "unsupported_request",
  "none",
] as const;

export type QualityIssue = (typeof QUALITY_ISSUES)[number];
export type QualityNextAction = (typeof QUALITY_NEXT_ACTIONS)[number];
export type SourceFailure = (typeof SOURCE_FAILURES)[number];
export type MissingInformationCode = (typeof MISSING_INFORMATION_CODES)[number];
export type FollowUpQuestionId = (typeof FOLLOW_UP_QUESTION_IDS)[number];
export type FollowUpOptionCode = (typeof FOLLOW_UP_OPTION_CODES)[number];
export type TraceStepId = (typeof TRACE_STEP_IDS)[number];
export type SkippedReason = (typeof SKIPPED_REASONS)[number];
export type RoutePath = (typeof ROUTE_PATHS)[number];

// ---------------------------------------------------------------- drift guards: a mismatch is a compile error
export type _Drift = [
  Expect<Equal<(typeof DECISION_STATES)[number], DecisionState>>,
  Expect<Equal<(typeof REASON_CODES)[number], ReasonCode>>,
  Expect<Equal<(typeof CATEGORIES)[number], Category>>,
  Expect<Equal<(typeof CONFIDENCE_BANDS)[number], ConfidenceBand>>,
  Expect<Equal<(typeof TRACE_STATUSES)[number], TraceStatus>>,
  Expect<Equal<(typeof WEATHER_SOURCES)[number], WeatherSource>>,
  Expect<Equal<(typeof SOURCE_TYPES)[number], SourceType>>,
  Expect<Equal<(typeof EXPERT_STATUSES)[number], ExpertStatus>>,
  Expect<Equal<(typeof REVIEW_DECISIONS)[number], ReviewDecision>>,
  Expect<Equal<(typeof IMAGE_KINDS)[number], ImageKind>>,
  Expect<Equal<(typeof FOLLOW_UP_ANSWER_TYPES)[number], FollowUpAnswerType>>,
];

// ---------------------------------------------------------------- roles
export type Role = "farmer" | "expert";
