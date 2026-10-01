/**
 * Pure helpers that turn an analysis response into what the Progress and Result screens show. Everything here reads
 * STRUCTURED fields (codes, numbers, booleans); no backend prose is used. Kept free of React so it can be unit tested.
 */
import type {
  AdvisorySource,
  CaseAnalysisOut,
  DecisionState,
  FollowUpOptions,
  ImageKind,
  QualityNextAction,
  TraceStep,
  WeatherResult,
} from "../api-types";
import { QUALITY_NEXT_ACTIONS } from "../api-types";

/** The text sent when the farmer presses "Request expert review". The backend's intent router reads it as an expert request. */
export const EXPERT_REQUEST_TEXT = "I want to talk to an agriculture expert.";

// ---------------------------------------------------------------- reading loosely typed detail objects
type Bag = Record<string, unknown> | null | undefined;
const str = (v: unknown): string | null => (typeof v === "string" && v ? v : null);
const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const strList = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : []);

export const stepOf = (trace: TraceStep[], id: string): TraceStep | undefined => trace.find((s) => s.step === id);

// ---------------------------------------------------------------- timeline
export type RowTone = "done" | "stopped" | "failed" | "skipped" | "decided";

export type TimelineRow = {
  step: string;
  tone: RowTone;
  status: TraceStep["status"];
  modelName: string | null;
  latencyMs: number | null;
  costUsd: number;
  skippedReason: string | null;
  detail: {
    intent?: string;
    confidence?: number;
    matched?: string[];
    passed?: boolean;
    score?: number;
    label?: string;
    band?: "low" | "medium" | "high";
    sourceCount?: number;
    verifiedCount?: number;
    demoCount?: number;
    weatherSource?: string;
    state?: string;
    reasonCode?: string;
    reasonDetail?: string;
  };
};

/**
 * One row per recorded step, in the order the backend recorded them. Nothing is added, merged or invented: a step the
 * backend marked skipped is shown as skipped, and `policy_decision` is shown as the final "decided" row.
 */
export function timelineRows(trace: TraceStep[]): TimelineRow[] {
  return [...trace]
    .sort((a, b) => a.position - b.position)
    .map((s) => {
      const d: Bag = s.detail;
      const detail: TimelineRow["detail"] = {};
      switch (s.step) {
        case "intent_router":
          detail.intent = str(d?.intent) ?? undefined;
          detail.confidence = num(d?.confidence) ?? undefined;
          detail.matched = strList(d?.matched);
          break;
        case "quality_gate":
          detail.passed = typeof d?.passed === "boolean" ? d.passed : undefined;
          detail.score = num(d?.score) ?? undefined;
          break;
        case "vision":
          detail.label = str(d?.label) ?? undefined;
          detail.confidence = num(d?.confidence) ?? s.confidence ?? undefined;
          detail.band = (s.confidence_band ?? (str(d?.confidence_band) as "low" | "medium" | "high" | null)) ?? undefined;
          break;
        case "advisory":
          detail.sourceCount = num(d?.source_count) ?? undefined;
          detail.verifiedCount = num(d?.verified_count) ?? undefined;
          detail.demoCount = num(d?.demo_count) ?? undefined;
          break;
        case "weather":
          detail.weatherSource = str(d?.source) ?? undefined;
          break;
        case "policy_decision":
          detail.state = str(d?.state) ?? undefined;
          detail.reasonCode = str(d?.reason_code) ?? undefined;
          detail.reasonDetail = str(d?.reason_detail) ?? undefined;
          break;
      }
      let tone: RowTone = "done";
      if (s.status === "skipped") tone = "skipped";
      else if (s.status === "failed") tone = "failed";
      else if (s.step === "quality_gate" && detail.passed === false) tone = "stopped"; // a fixable problem, not an error
      else if (s.step === "policy_decision") tone = "decided";
      return {
        step: s.step,
        tone,
        status: s.status,
        modelName: s.model_name ?? null,
        latencyMs: s.latency_ms ?? null,
        costUsd: s.cost_usd,
        skippedReason: s.skipped_reason ?? null,
        detail,
      };
    });
}

// ---------------------------------------------------------------- sources
/**
 * A source is shown as Verified ONLY if the backend says verified AND it is an ingested document. A demo source is never
 * Verified, even if some bug upstream marked it so. This is the one place that decision is made.
 */
export function isVerifiedSource(source: Pick<AdvisorySource, "verified" | "source_type">): boolean {
  return source.verified === true && source.source_type === "ingested";
}

export type SourceKind = "verified" | "demo" | "unverified";
export function sourceKind(source: Pick<AdvisorySource, "verified" | "source_type">): SourceKind {
  if (source.source_type === "demo") return "demo";
  return isVerifiedSource(source) ? "verified" : "unverified";
}

/** `published_at` is when the source document was published. Missing means "Date not available", never a guess. */
export function publishedDate(source: Pick<AdvisorySource, "published_at">): string | null {
  return source.published_at ? source.published_at : null;
}

export function safeSourceUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    return u.protocol === "https:" || u.protocol === "http:" ? u.toString() : null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------- weather
export function weatherOf(analysis: CaseAnalysisOut): WeatherResult | null {
  const call = analysis.result.calls?.find((c) => c.route === "weather");
  const out = call?.output;
  if (!out || Array.isArray(out) || typeof out !== "object") return null;
  const w = out as Partial<WeatherResult>;
  return typeof w.available === "boolean" && typeof w.source === "string" ? (w as WeatherResult) : null;
}

// ---------------------------------------------------------------- what the farmer can do next
export type NextAction =
  | { kind: "photo"; photoKind: ImageKind; tip: QualityNextAction | null }
  | { kind: "followUp"; options: FollowUpOptions }
  | { kind: "expertAnswer" }
  | { kind: "none" };

const isNextAction = (v: string | null): v is QualityNextAction => !!v && (QUALITY_NEXT_ACTIONS as readonly string[]).includes(v);

export function nextAction(analysis: CaseAnalysisOut): NextAction {
  if (analysis.state === "NEEDS_BETTER_IMAGE") {
    const detail = stepOf(analysis.trace, "quality_gate")?.detail;
    const tip = str(detail?.next_action);
    return { kind: "photo", photoKind: "leaf_closeup", tip: isNextAction(tip) ? tip : null };
  }
  if (analysis.expert?.status === "awaiting_farmer") return { kind: "expertAnswer" };
  if (analysis.follow_up_options && analysis.state !== "EXPERT_REVIEW" && analysis.state !== "UNSUPPORTED") {
    return { kind: "followUp", options: analysis.follow_up_options };
  }
  return { kind: "none" };
}

/** "Request expert review" is offered while an expert is not already on the case and the question is one an expert can help with. */
const CAN_REQUEST_EXPERT: ReadonlySet<DecisionState> = new Set<DecisionState>([
  "NEEDS_BETTER_IMAGE",
  "NEEDS_MORE_CONTEXT",
  "PRELIMINARY_GUIDANCE",
]);
export function canRequestExpert(analysis: Pick<CaseAnalysisOut, "state">): boolean {
  return CAN_REQUEST_EXPERT.has(analysis.state);
}

/** The possible condition is named ONLY in a preliminary-guidance answer. Escalations and requests for evidence never name one. */
export function showsCondition(analysis: CaseAnalysisOut): boolean {
  return analysis.state === "PRELIMINARY_GUIDANCE" && !!analysis.result.preliminary_label;
}

/** Position (0 to 100) of the marker on the confidence scale. */
export function bandMarkerPercent(confidence: number | null | undefined): number | null {
  if (confidence == null || !Number.isFinite(confidence)) return null;
  return Math.round(Math.min(1, Math.max(0, confidence)) * 100);
}

export const BAND_THRESHOLDS = { low: 0.6, high: 0.85 } as const;

/** Errors where the farmer's check is certainly still saved (the request just did not get through). Not for a bad link or a missing case. */
export function checkIsSafe(code: string): boolean {
  return ["network", "timeout", "unavailable", "server", "unknown", "aborted"].includes(code);
}
