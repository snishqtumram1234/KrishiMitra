/**
 * Pure logic for the expert review queue: reason tags, the review form's validation, and the request body.
 * The backend stays the authority (it answers 409 / 422); these checks only save a round trip and explain the rule.
 */
import type { Category, ExpertStatus, ReviewDecision, ReviewIn } from "./api-types";

export const NOTES_MAX = 4000;
export const FIELD_MAX = 200;

/** Reason codes that have a tag in the dictionary (`expert.tag.<code>`); anything else shows the generic tag. */
export const TAG_CODES = [
  "treatment_needs_expert",
  "farmer_requested_expert",
  "low_confidence_escalate",
  "models_conflict",
  "label_unknown",
  "sources_unavailable",
] as const;
export type TagCode = (typeof TAG_CODES)[number];

export function tagKey(code: string | null | undefined): `expert.tag.${TagCode | "other"}` {
  return `expert.tag.${(TAG_CODES as readonly string[]).includes(code ?? "") ? (code as TagCode) : "other"}`;
}

export const STATUS_FILTERS = ["pending_review", "awaiting_farmer", "follow_up_received", "reviewed", "all"] as const;
export type StatusFilter = (typeof STATUS_FILTERS)[number];
export const isStatusFilter = (v: unknown): v is StatusFilter => (STATUS_FILTERS as readonly string[]).includes(v as string);

/** Only an escalation that is waiting for a review can be reviewed. Everything else is read-only. */
export const canReview = (status: ExpertStatus): boolean => status === "pending_review";

/** The categories an expert can name for "Likely condition". `unknown` is its own decision, not a category. */
export const REVIEW_CATEGORIES: readonly Category[] = ["healthy", "rust_like", "leaf_spot_like", "insect_damage"];

export const DECISIONS: readonly ReviewDecision[] = ["likely", "insufficient", "unknown", "request_more"];

export type ReviewInput = {
  decision: ReviewDecision | "";
  label: Category | "";
  notes: string;
  advisoryTitle: string;
  advisoryPublisher: string;
  advisoryUrl: string;
};
export type ReviewProblem = "decision" | "category" | "notes" | "notesLong" | "advisory" | "url";
export type ReviewProblems = Partial<Record<"decision" | "label" | "notes" | "advisory" | "url", ReviewProblem>>;

export function isHttpUrl(value: string): boolean {
  try {
    const u = new URL(value);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

export function checkReview(input: ReviewInput): ReviewProblems {
  const p: ReviewProblems = {};
  if (!input.decision) p.decision = "decision";
  if (input.decision === "likely" && !input.label) p.label = "category";
  const notes = input.notes.trim();
  if (input.decision === "request_more" && !notes) p.notes = "notes";
  if (notes.length > NOTES_MAX) p.notes = "notesLong";
  const t = input.advisoryTitle.trim();
  const pub = input.advisoryPublisher.trim();
  const url = input.advisoryUrl.trim();
  if ((t || pub || url) && (!t || !pub)) p.advisory = "advisory";
  if (url && !isHttpUrl(url)) p.url = "url";
  return p;
}

/** The request body: only the fields the chosen decision allows (`label` only with `likely`). */
export function buildReview(input: ReviewInput): ReviewIn {
  if (!input.decision) throw new Error("decision is required");
  const body: ReviewIn = { decision: input.decision, notes: input.notes.trim() };
  if (input.decision === "likely" && input.label) body.label = input.label;
  const title = input.advisoryTitle.trim();
  const publisher = input.advisoryPublisher.trim();
  if (title && publisher) {
    const url = input.advisoryUrl.trim();
    body.recommended_advisory = { title, publisher, ...(url ? { url } : {}) };
  }
  return body;
}

/** One line of a prediction's `output` as `key: value` pairs of codes and numbers (the backend sends no prose here). */
export function outputPairs(output: unknown): [string, string][] {
  if (!output || typeof output !== "object" || Array.isArray(output)) return [];
  return Object.entries(output as Record<string, unknown>).flatMap(([k, v]): [string, string][] => {
    if (v == null) return [];
    if (Array.isArray(v)) return [[k, v.map(String).join(", ")]];
    if (typeof v === "object") return [];
    return [[k, String(v)]];
  });
}

export function countByStatus<T extends { status: ExpertStatus }>(rows: T[]): Record<StatusFilter, number> {
  const out: Record<StatusFilter, number> = { pending_review: 0, awaiting_farmer: 0, follow_up_received: 0, reviewed: 0, all: rows.length };
  for (const r of rows) out[r.status]++;
  return out;
}
