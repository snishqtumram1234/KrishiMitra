import { describe, expect, it } from "vitest";
import { buildReview, canReview, checkReview, countByStatus, NOTES_MAX, outputPairs, tagKey, type ReviewInput } from "./expert";

const base: ReviewInput = { decision: "", label: "", notes: "", advisoryTitle: "", advisoryPublisher: "", advisoryUrl: "" };
const with_ = (o: Partial<ReviewInput>): ReviewInput => ({ ...base, ...o });

describe("checkReview", () => {
  it("needs a decision", () => expect(checkReview(base)).toEqual({ decision: "decision" }));
  it("likely needs a category; the other decisions do not", () => {
    expect(checkReview(with_({ decision: "likely" }))).toEqual({ label: "category" });
    expect(checkReview(with_({ decision: "likely", label: "rust_like" }))).toEqual({});
    for (const d of ["insufficient", "unknown"] as const) expect(checkReview(with_({ decision: d }))).toEqual({});
  });
  it("request_more needs notes saying what to send", () => {
    expect(checkReview(with_({ decision: "request_more", notes: "   " }))).toEqual({ notes: "notes" });
    expect(checkReview(with_({ decision: "request_more", notes: "Which leaves?" }))).toEqual({});
  });
  it("notes are limited to 4000 characters", () => {
    expect(checkReview(with_({ decision: "insufficient", notes: "x".repeat(NOTES_MAX + 1) }))).toEqual({ notes: "notesLong" });
    expect(checkReview(with_({ decision: "insufficient", notes: "x".repeat(NOTES_MAX) }))).toEqual({});
  });
  it("an advisory needs both title and publisher, and a link must be http(s)", () => {
    expect(checkReview(with_({ decision: "unknown", advisoryTitle: "T" }))).toEqual({ advisory: "advisory" });
    expect(checkReview(with_({ decision: "unknown", advisoryTitle: "T", advisoryPublisher: "P" }))).toEqual({});
    expect(checkReview(with_({ decision: "unknown", advisoryTitle: "T", advisoryPublisher: "P", advisoryUrl: "javascript:alert(1)" }))).toEqual({ url: "url" });
    expect(checkReview(with_({ decision: "unknown", advisoryTitle: "T", advisoryPublisher: "P", advisoryUrl: "https://example.org/a" }))).toEqual({});
  });
});

describe("buildReview", () => {
  it("sends a label only with likely, trimmed notes, and the advisory only when complete", () => {
    expect(buildReview(with_({ decision: "likely", label: "rust_like", notes: " ok " }))).toEqual({ decision: "likely", label: "rust_like", notes: "ok" });
    expect(buildReview(with_({ decision: "insufficient", label: "rust_like" }))).toEqual({ decision: "insufficient", notes: "" });
    expect(buildReview(with_({ decision: "unknown", advisoryTitle: "T", advisoryPublisher: "P", advisoryUrl: " https://e.org " }))).toEqual({
      decision: "unknown", notes: "", recommended_advisory: { title: "T", publisher: "P", url: "https://e.org" },
    });
    expect(buildReview(with_({ decision: "unknown", advisoryTitle: "T", advisoryPublisher: "P" })).recommended_advisory).toEqual({ title: "T", publisher: "P" });
  });
});

describe("queue helpers", () => {
  it("only a pending escalation can be reviewed", () => {
    expect(canReview("pending_review")).toBe(true);
    for (const s of ["awaiting_farmer", "reviewed", "follow_up_received"] as const) expect(canReview(s)).toBe(false);
  });
  it("tags known reasons and falls back to a generic tag", () => {
    expect(tagKey("treatment_needs_expert")).toBe("expert.tag.treatment_needs_expert");
    expect(tagKey("something_new")).toBe("expert.tag.other");
    expect(tagKey(null)).toBe("expert.tag.other");
  });
  it("counts per status for the chips", () => {
    expect(countByStatus([{ status: "pending_review" }, { status: "pending_review" }, { status: "reviewed" }])).toEqual({
      pending_review: 2, awaiting_farmer: 0, follow_up_received: 0, reviewed: 1, all: 3,
    });
  });
  it("shows a prediction's output as codes and numbers, skipping nested objects", () => {
    expect(outputPairs({ intent: "weather_context", confidence: 0.7, matched: ["rain", "week"], deep: { a: 1 }, none: null })).toEqual([
      ["intent", "weather_context"], ["confidence", "0.7"], ["matched", "rain, week"],
    ]);
    expect(outputPairs([1, 2])).toEqual([]);
    expect(outputPairs(null)).toEqual([]);
  });
});
