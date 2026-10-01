import { describe, expect, it } from "vitest";
import type { AdvisorySource, CaseAnalysisOut, TraceStep } from "../api-types";
import { canRequestExpert, isVerifiedSource, nextAction, publishedDate, safeSourceUrl, showsCondition, sourceKind, timelineRows, weatherOf } from "./result";

const src = (o: Partial<AdvisorySource>): AdvisorySource => ({
  title: "t", publisher: "p", verified: false, stale: false, structured: false, source_type: "demo", ...o,
});

describe("source labels", () => {
  it("never calls a demo source verified, even if the flag says so", () => {
    expect(sourceKind(src({ source_type: "demo", verified: true }))).toBe("demo");
    expect(isVerifiedSource(src({ source_type: "demo", verified: true }))).toBe(false);
  });
  it("is verified only for an ingested, verified source", () => {
    expect(sourceKind(src({ source_type: "ingested", verified: true }))).toBe("verified");
    expect(sourceKind(src({ source_type: "ingested", verified: false }))).toBe("unverified");
  });
  it("has a published date only when the source gives one", () => {
    expect(publishedDate(src({ published_at: null }))).toBeNull();
    expect(publishedDate(src({}))).toBeNull();
    expect(publishedDate(src({ published_at: "2026-03-01" }))).toBe("2026-03-01");
  });
  it("links only http(s) URLs", () => {
    expect(safeSourceUrl("https://example.org/a")).toBe("https://example.org/a");
    expect(safeSourceUrl("javascript:alert(1)")).toBeNull();
    expect(safeSourceUrl("not a url")).toBeNull();
    expect(safeSourceUrl(null)).toBeNull();
  });
});

const step = (o: Partial<TraceStep> & { step: string; position: number }): TraceStep => ({ status: "completed", cost_usd: 0, ...o }) as TraceStep;

describe("timelineRows", () => {
  const trace: TraceStep[] = [
    step({ step: "policy_decision", position: 5, detail: { state: "NEEDS_BETTER_IMAGE", reason_code: "quality_failed", reason_detail: "blurry" } }),
    step({ step: "intent_router", position: 0, latency_ms: 0, model_name: "keyword-intent-rules", detail: { intent: "crop_health_image", confidence: 0.8, matched: ["spot"] } }),
    step({ step: "quality_gate", position: 1, latency_ms: 35, detail: { passed: false, score: 40 } }),
    step({ step: "vision", position: 2, status: "skipped", skipped_reason: "stopped_earlier" }),
    step({ step: "weather", position: 4, status: "failed", error: "boom" }),
  ];
  const rows = timelineRows(trace);
  it("keeps the recorded order and one row per recorded step", () => {
    expect(rows.map((r) => r.step)).toEqual(["intent_router", "quality_gate", "vision", "weather", "policy_decision"]);
  });
  it("carries the real latencies and model names", () => {
    expect(rows[1].latencyMs).toBe(35);
    expect(rows[0].modelName).toBe("keyword-intent-rules");
    expect(rows[0].detail.matched).toEqual(["spot"]);
  });
  it("tones: a failed quality check is a fixable stop, skipped stays skipped, an errored step is failed, the policy row is decided", () => {
    expect(rows.map((r) => r.tone)).toEqual(["done", "stopped", "skipped", "failed", "decided"]);
    expect(rows[2].skippedReason).toBe("stopped_earlier");
  });
  it("does not invent steps for an empty trace", () => {
    expect(timelineRows([])).toEqual([]);
  });
});

const analysis = (o: Partial<CaseAnalysisOut> & { state: CaseAnalysisOut["state"] }, result: Partial<CaseAnalysisOut["result"]> = {}): CaseAnalysisOut =>
  ({
    routing_run_id: "r",
    case_id: "c",
    created_at: "2026-10-01T06:55:43Z",
    result: { state: o.state, reason: "x", message: "m", total_latency_ms: 1, total_cost_usd: 0, estimated_cost_saved_usd: 0, ...result },
    missing_information: [],
    trace: [],
    ...o,
  }) as CaseAnalysisOut;

describe("next action and expert request", () => {
  it("asks for a new close-up when the photo was not usable, with the backend's tip", () => {
    const a = analysis({ state: "NEEDS_BETTER_IMAGE", trace: [step({ step: "quality_gate", position: 1, detail: { passed: false, next_action: "retake_steady" } })] });
    expect(nextAction(a)).toEqual({ kind: "photo", photoKind: "leaf_closeup", tip: "retake_steady" });
  });
  it("ignores an unknown tip rather than showing a raw code", () => {
    const a = analysis({ state: "NEEDS_BETTER_IMAGE", trace: [step({ step: "quality_gate", position: 1, detail: { next_action: "do_a_dance" } })] });
    expect(nextAction(a)).toMatchObject({ tip: null });
  });
  it("offers the structured question for guidance and for missing context, never for escalations or unsupported", () => {
    const fu = { question_id: "leaf_position", answer_type: "choice" as const, options: ["both"] };
    expect(nextAction(analysis({ state: "PRELIMINARY_GUIDANCE", follow_up_options: fu }))).toEqual({ kind: "followUp", options: fu });
    expect(nextAction(analysis({ state: "NEEDS_MORE_CONTEXT", follow_up_options: fu }))).toEqual({ kind: "followUp", options: fu });
    expect(nextAction(analysis({ state: "EXPERT_REVIEW", follow_up_options: fu }))).toEqual({ kind: "none" });
    expect(nextAction(analysis({ state: "UNSUPPORTED", follow_up_options: fu }))).toEqual({ kind: "none" });
  });
  it("answers an expert's request for more information", () => {
    expect(nextAction(analysis({ state: "EXPERT_REVIEW", expert: { status: "awaiting_farmer" } }))).toEqual({ kind: "expertAnswer" });
  });
  it("offers expert review for the three non-final states only", () => {
    expect(canRequestExpert({ state: "NEEDS_BETTER_IMAGE" })).toBe(true);
    expect(canRequestExpert({ state: "NEEDS_MORE_CONTEXT" })).toBe(true);
    expect(canRequestExpert({ state: "PRELIMINARY_GUIDANCE" })).toBe(true);
    expect(canRequestExpert({ state: "EXPERT_REVIEW" })).toBe(false);
    expect(canRequestExpert({ state: "UNSUPPORTED" })).toBe(false);
  });
  it("names a possible condition only in preliminary guidance", () => {
    expect(showsCondition(analysis({ state: "PRELIMINARY_GUIDANCE" }, { preliminary_label: "rust_like" }))).toBe(true);
    expect(showsCondition(analysis({ state: "EXPERT_REVIEW" }, { preliminary_label: "rust_like" }))).toBe(false);
    expect(showsCondition(analysis({ state: "PRELIMINARY_GUIDANCE" }))).toBe(false);
  });
});

describe("weatherOf", () => {
  it("reads the weather call's structured output, and nothing else", () => {
    const calls = [{ route: "weather", model: "w", latency_ms: 1, cost_usd: 0, outcome: "ok", output: { available: true, source: "live", stale: false, summary: "x" } }];
    expect(weatherOf(analysis({ state: "PRELIMINARY_GUIDANCE" }, { calls }))?.source).toBe("live");
    expect(weatherOf(analysis({ state: "PRELIMINARY_GUIDANCE" }, { calls: [] }))).toBeNull();
  });
});
