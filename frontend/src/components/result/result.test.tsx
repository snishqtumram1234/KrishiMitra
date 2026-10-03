// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { CaseAnalysisOut, CaseOut, DecisionState, TraceStep } from "@/lib/api-types";
import { I18nProvider } from "@/i18n/client";
import type { Locale } from "@/i18n/locales";
import { ResultReady } from "./ResultView";
import { EXCERPTS_MR } from "@/i18n/excerpts-mr";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }) }));
vi.mock("@/lib/api-client", () => ({
  ApiError: class extends Error {},
  getApiClient: () => ({
    imageSignedUrl: () => Promise.reject(new Error("no image in tests")),
    getWeather: () => Promise.resolve({ available: true, source: "live", provider: "Open-Meteo", stale: false, temperature_c: 24, humidity_pct: 88, summary: "x" }),
  }),
}));

const step = (o: Partial<TraceStep> & { step: string; position: number }): TraceStep => ({ status: "completed", cost_usd: 0, ...o }) as TraceStep;
const item = { id: "c1", district: "Pune", symptom_context: "Yellow spots on leaves", growth_stage: "R3", images: [] } as unknown as CaseOut;

const imageTrace = (qualityPassed: boolean, extra: TraceStep[] = []): TraceStep[] => [
  step({ step: "intent_router", position: 0, latency_ms: 0, model_name: "keyword-intent-rules", detail: { intent: "crop_health_image", confidence: 0.8, matched: ["spot"] } }),
  step({ step: "quality_gate", position: 1, latency_ms: 35, model_name: "opencv-quality-gate", detail: { passed: qualityPassed, score: qualityPassed ? 92 : 40, issues: qualityPassed ? [] : ["blurry"], next_action: qualityPassed ? "continue" : "retake_steady" } }),
  ...extra,
];
const last = (state: DecisionState, code: string, detail: string | null = null): TraceStep =>
  step({ step: "policy_decision", position: 5, detail: { state, reason_code: code, reason_detail: detail } });

function make(state: DecisionState, o: Partial<CaseAnalysisOut>, result: Record<string, unknown> = {}): CaseAnalysisOut {
  return {
    routing_run_id: "r1", case_id: "c1", state, created_at: "2026-09-30T20:30:00Z", expert: null,
    missing_information: [], trace: [],
    result: { state, reason: "x", message: "BACKEND ENGLISH MESSAGE MUST NOT APPEAR", follow_up_question: "BACKEND QUESTION MUST NOT APPEAR", total_latency_ms: 55, total_cost_usd: 2e-5, estimated_cost_saved_usd: 0, sources: [], intent: "crop_health_image", intent_confidence: 0.8, intent_rule: "keywords:crop_health_image", path: "image_diagnosis", ...result },
    ...o,
  } as CaseAnalysisOut;
}

const FIXTURES: Record<DecisionState, CaseAnalysisOut> = {
  NEEDS_BETTER_IMAGE: make("NEEDS_BETTER_IMAGE", { reason_code: "quality_failed", reason_detail: "blurry", missing_information: ["clearer_close_up_photo"], trace: [...imageTrace(false), last("NEEDS_BETTER_IMAGE", "quality_failed", "blurry")] }),
  NEEDS_MORE_CONTEXT: make("NEEDS_MORE_CONTEXT", { reason_code: "intent_unclear", missing_information: ["symptom_description"], follow_up_options: { question_id: "describe_problem", answer_type: "text" }, trace: [step({ step: "intent_router", position: 0, latency_ms: 0, detail: { intent: "general_crop_question", confidence: 0.3, matched: [] } }), last("NEEDS_MORE_CONTEXT", "intent_unclear")] }, { path: "general_crop_question", intent: "general_crop_question" }),
  PRELIMINARY_GUIDANCE: make("PRELIMINARY_GUIDANCE", {
    reason_code: "mid_confidence", confidence_band: "medium", missing_information: ["affected_leaf_position", "field_overview_photo"],
    follow_up_options: { question_id: "leaf_position", answer_type: "choice", options: ["older_leaves", "younger_leaves", "both"] },
    trace: [...imageTrace(true, [step({ step: "vision", position: 2, latency_ms: 20, confidence: 0.65, confidence_band: "medium", detail: { label: "rust_like", confidence: 0.65 } }), step({ step: "advisory", position: 3, latency_ms: 0, detail: { source_count: 1, verified_count: 0, demo_count: 1 } })]), last("PRELIMINARY_GUIDANCE", "mid_confidence")],
  }, { preliminary_label: "rust_like", confidence: 0.65, confidence_band: "medium", sources: [{ title: "Demo advisory: rust_like", publisher: "KrishiMitra demo data (not a real advisory)", verified: false, stale: false, structured: false, source_type: "demo", published_at: null, source_url: null, retrieved_at: "2026-10-01T06:55:43Z" }] }),
  EXPERT_REVIEW: make("EXPERT_REVIEW", { reason_code: "low_confidence_escalate", confidence_band: "low", expert: { status: "pending_review" }, trace: [...imageTrace(true), last("EXPERT_REVIEW", "low_confidence_escalate")] }, { preliminary_label: "rust_like", confidence: 0.4 }),
  UNSUPPORTED: make("UNSUPPORTED", { reason_code: "unsupported_request", trace: [step({ step: "intent_router", position: 0, latency_ms: 0, detail: { intent: "unsupported_request", confidence: 0.9, matched: ["loan"] } }), last("UNSUPPORTED", "unsupported_request")] }, { path: "unsupported_request", intent: "unsupported_request" }),
};

const NEGATED = /(?:not|never) an? (?:lab-)?confirmed diagnosis/gi;
const view = (a: CaseAnalysisOut, locale: Locale = "en") =>
  render(<I18nProvider locale={locale}><ResultReady caseId="c1" analysis={a} item={item} /></I18nProvider>);

describe.each(["en", "mr"] as const)("Result screen (%s)", (locale) => {
  for (const state of Object.keys(FIXTURES) as DecisionState[]) {
    it(`${state}: renders from structured fields only, with no raw keys and no unnegated 'confirmed diagnosis'`, () => {
      const { container } = view(FIXTURES[state], locale);
      const text = container.textContent ?? "";
      expect(text).not.toMatch(/BACKEND (ENGLISH MESSAGE|QUESTION)/);
      expect(text).not.toMatch(/\b(state|reason|band|missing|source|result|next|expert|route|trace|timeline|weather|check)\.[A-Za-z_]+/);
      expect(text.replace(NEGATED, "")).not.toMatch(/confirmed diagnosis/i);
    });
  }
});

describe("Result screen states (en)", () => {
  it("NEEDS_BETTER_IMAGE: reason, the tip from the backend's next_action, and a photo upload", () => {
    view(FIXTURES.NEEDS_BETTER_IMAGE);
    expect(screen.getByText("Needs a better photo")).toBeInTheDocument();
    expect(screen.getByText("Retake, holding steady")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send photo" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Request expert review" })).toBeInTheDocument();
  });
  it("NEEDS_MORE_CONTEXT: asks the structured question as a text answer", () => {
    view(FIXTURES.NEEDS_MORE_CONTEXT);
    expect(screen.getByText("What do you see on the plant, or what would you like to know?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send answer" })).toBeInTheDocument();
  });
  it("PRELIMINARY_GUIDANCE: names a possible condition with its band, offers the choices, shows a demo source with no Verified pill", () => {
    view(FIXTURES.PRELIMINARY_GUIDANCE);
    fireEvent.click(screen.getByRole("button", { name: "Show more details" }));
    expect(screen.getAllByText("Rust-like signs").length).toBeGreaterThan(0); // hero heading, and again in More details
    expect(screen.getByText("Medium · 0.65")).toBeInTheDocument();
    expect(screen.getByText("65%")).toBeInTheDocument(); // the headline confidence score
    expect(screen.getByText("Medium confidence")).toBeInTheDocument();
    expect(screen.getByText("Most likely condition")).toBeInTheDocument();
    expect(screen.getByText("Preliminary assessment")).toBeInTheDocument();
    for (const label of ["Older leaves", "Younger leaves", "Both"]) expect(screen.getByText(label)).toBeInTheDocument();
    expect(screen.getByText("Demo source, not verified")).toBeInTheDocument();
    expect(screen.queryByText("Verified")).not.toBeInTheDocument();
    expect(screen.getByText("Date not available")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Request expert review" })).toBeInTheDocument();
  });
  it("EXPERT_REVIEW: shows the expert's status, never names a condition, no request button", () => {
    view(FIXTURES.EXPERT_REVIEW);
    expect(screen.getByText("With an expert", { selector: "h2" })).toBeInTheDocument();
    expect(screen.getByText(/Pending review/)).toBeInTheDocument();
    expect(screen.queryByText("Rust-like signs")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Request expert review" })).not.toBeInTheDocument();
  });
  it("UNSUPPORTED: says so plainly, no observed card, no request button", () => {
    view(FIXTURES.UNSUPPORTED);
    expect(screen.getByText("Not supported", { selector: "h2" })).toBeInTheDocument();
    expect(screen.queryByText("What we observed")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Request expert review" })).not.toBeInTheDocument();
  });
  it("route details toggle shows the recorded steps", () => {
    view(FIXTURES.PRELIMINARY_GUIDANCE);
    fireEvent.click(screen.getByRole("button", { name: "Show more details" }));
    const toggle = screen.getByRole("button", { name: /Route details/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("keywords:crop_health_image")).not.toBeInTheDocument();
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("keywords:crop_health_image")).toBeInTheDocument();
    expect(screen.getByText("opencv-quality-gate")).toBeInTheDocument();
    expect(screen.getByText(/PRELIMINARY_GUIDANCE · mid_confidence/)).toBeInTheDocument();
  });
  it("shows a real excerpt word for word with its PDF page, and nothing for a demo source", () => {
    const a = structuredClone(FIXTURES.PRELIMINARY_GUIDANCE);
    a.result.sources = [
      { title: "Bulletin (2023)", publisher: "ICAR-IISR", verified: false, stale: false, structured: false, source_type: "ingested", published_at: null, source_url: "https://example.org/b.pdf", excerpt: "Initially chlorotic gray brown spots appear on the leaves.", page: 53, retrieved_at: "2026-10-01T06:55:43Z" },
      { title: "Demo advisory", publisher: "demo", verified: false, stale: false, structured: false, source_type: "demo", published_at: null, source_url: null, retrieved_at: "2026-10-01T06:55:43Z" },
    ];
    view(a);
    // the hero quotes the source word for word, with publisher and PDF page
    expect(screen.getByText("Initially chlorotic gray brown spots appear on the leaves.")).toBeInTheDocument();
    expect(screen.getByText(/ICAR-IISR, PDF page 53/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show more details" }));
    expect(screen.getAllByText("From the source, word for word", { exact: false })).toHaveLength(1);
    expect(screen.queryByText("Verified")).not.toBeInTheDocument();
  });
  it("shows only 'What is happening' and 'What you can do', with the verified good practices as numbered steps", () => {
    const a = structuredClone(FIXTURES.PRELIMINARY_GUIDANCE);
    a.result.sources = [
      { title: "Bulletin (2023)", publisher: "ICAR-IISR", verified: true, stale: false, structured: false, source_type: "ingested", published_at: null, source_url: "https://example.org/b.pdf", excerpt: "Spots appear on the leaves.", excerpt_kind: "description", page: 53, retrieved_at: "2026-10-01T06:55:43Z" },
      { title: "Bulletin (2023)", publisher: "ICAR-IISR", verified: true, stale: false, structured: false, source_type: "ingested", published_at: null, source_url: "https://example.org/b.pdf", excerpt: "1.Use clean seed. 2.Remove volunteer plants.", excerpt_kind: "management", page: 53, retrieved_at: "2026-10-01T06:55:43Z" },
    ];
    view(a);
    expect(screen.getByText("What is happening")).toBeInTheDocument();
    expect(screen.getByText("What you can do")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Rust-like signs" })).toBeInTheDocument();
    expect(screen.getByText("65% match")).toBeInTheDocument();
    expect(screen.getByText("Use clean seed.")).toBeInTheDocument();
    expect(screen.getByText("Remove volunteer plants.")).toBeInTheDocument();
    expect(screen.getByText(/never gives pesticide names or doses/)).toBeInTheDocument();
    expect(screen.queryByText("Preliminary assessment")).not.toBeInTheDocument(); // folded into "More details"
    expect(screen.queryByText("Route details")).not.toBeInTheDocument();
  });
  it("adds the report header, help contacts and, for rust, today's weather risk from the source's numbers", async () => {
    const a = structuredClone(FIXTURES.PRELIMINARY_GUIDANCE);
    a.result.sources = [
      { title: "Bulletin (2023)", publisher: "ICAR-IISR", verified: true, stale: false, structured: false, source_type: "ingested", published_at: null, source_url: "https://example.org/b.pdf", excerpt: "Spots appear.", excerpt_kind: "description", page: 53, retrieved_at: "2026-10-01T06:55:43Z" },
    ];
    view(a);
    expect(screen.getByText("Crop health report")).toBeInTheDocument();
    expect(screen.getByText("Case C1")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Kisan Call Centre/ })).toHaveAttribute("href", "tel:18001801551");
    expect(screen.getByRole("link", { name: /Krishi Vigyan Kendra/ })).toHaveAttribute("href", "https://kvk.icar.gov.in/");
    expect(await screen.findByText("Today's weather favours the spread of this condition")).toBeInTheDocument(); // 24 °C, 88%
    expect(screen.getByText(/22–27 °C with 80% humidity or more/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Share/ })).toBeInTheDocument();
  });
  it("shows a published date for a verified, ingested source", () => {
    const a = structuredClone(FIXTURES.PRELIMINARY_GUIDANCE);
    a.result.sources = [{ title: "KVK note", publisher: "A KVK", verified: true, stale: false, structured: true, source_type: "ingested", published_at: "2026-03-01", source_url: "https://example.org/n", retrieved_at: "2026-10-01T06:55:43Z" }];
    view(a);
    fireEvent.click(screen.getByRole("button", { name: "Show more details" }));
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(screen.getByText("Published 01 Mar 2026")).toBeInTheDocument();
    expect(screen.queryByText("Date not available")).not.toBeInTheDocument();
  });
});

describe("photo result with weather", () => {
  const withWeather = (label: string, sources: unknown[]) =>
    make("PRELIMINARY_GUIDANCE", { reason_code: "high_confidence", confidence_band: "high" }, {
      preliminary_label: label, confidence: 0.92, confidence_band: "high", sources,
      calls: [{ route: "weather", model_name: "open-meteo", latency_ms: 5, cost_usd: 0, outcome: "ok",
        output: { available: true, source: "cached", stale: true, district: "Pune", temperature_c: 25, humidity_pct: 77, summary: "x" } }],
    });

  it("leads with the cause from the source, not the weather", () => {
    const cause = "This is a disease of fungal origin caused by Phakopsora pachyrhizi.";
    view(withWeather("rust_like", [{ title: "Bulletin", publisher: "ICAR", verified: true, stale: false, structured: false,
      source_type: "ingested", published_at: null, source_url: "u", retrieved_at: "2026-10-01T06:55:43Z",
      excerpt: cause, excerpt_kind: "description", page: 53 }]));
    const happening = screen.getByText(/What is happening/i).closest("section")!;
    expect(happening.textContent).toContain(cause);
    expect(happening.textContent).not.toMatch(/Old reading|Humidity/);
  });

  it("says plainly that a healthy leaf shows no signs of disease", () => {
    view(withWeather("healthy", []));
    expect(screen.getByText(/no signs of rust, leaf spot or insect damage/i)).toBeTruthy();
  });
});

describe("Marathi result", () => {
  it("shows the cause in Marathi, marked as a translation with the English original kept", () => {
    const cause = Object.keys(EXCERPTS_MR).find((k) => k.includes("Phakopsora pachyrhizi"))!;
    const a = make("PRELIMINARY_GUIDANCE", { reason_code: "high_confidence", confidence_band: "high" }, {
      preliminary_label: "rust_like", confidence: 0.92, confidence_band: "high",
      sources: [{ title: "Bulletin", publisher: "ICAR", verified: true, stale: false, structured: false, source_type: "ingested",
        published_at: null, source_url: "u", retrieved_at: "2026-10-01T06:55:43Z", excerpt: cause, excerpt_kind: "description", page: 53 }],
    });
    const { container } = view(a, "mr");
    const quote = container.querySelector('blockquote[lang="mr"]');
    expect(quote?.textContent).toBe(EXCERPTS_MR[cause]);
    const note = [...container.querySelectorAll("details")].find((d) => d.textContent?.includes(cause));
    expect(note?.querySelector("summary")?.textContent).toMatch(/अनुवाद/);
  });
});
