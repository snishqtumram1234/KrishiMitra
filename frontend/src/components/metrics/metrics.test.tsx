// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "@/i18n/client";
import type { CostLatencyOut, Overview, RoutesOut } from "@/lib/api-types";
import { MetricsDashboard } from "./MetricsDashboard";

const api = { metricsOverview: vi.fn(), metricsRoutes: vi.fn(), metricsCostLatency: vi.fn() };
vi.mock("@/lib/api-client", () => ({
  ApiError: class ApiError extends Error {
    constructor(readonly code: string) {
      super(code);
    }
  },
  getApiClient: () => api,
}));
// jsdom cannot lay out SVG charts; the wrappers are thin, and every chart has a table with the same numbers.
vi.mock("./charts", () => ({
  CHART: { brand: "", info: "", soil: "", warning: "", danger: "", grid: "", text: "" },
  HBar: ({ caption, data }: { caption: string; data: { name: string; value: number }[] }) => <div data-testid="hbar" aria-label={caption}>{data.map((d) => `${d.name}=${d.value}`).join(";")}</div>,
  GroupBars: ({ caption }: { caption: string }) => <div data-testid="groupbars" aria-label={caption} />,
}));

const lat = (p50: number, p95: number) => ({ n: 3, avg_ms: 80.67, p50_ms: p50, p95_ms: p95, max_ms: 187 });
const rate = (n: number, d: number) => ({ numerator: n, denominator: d, rate: d ? n / d : null });

const overview: Overview = {
  window: { days: null, since: null, generated_at: "2026-09-30T20:31:06Z" },
  total_cases: 3, total_analyses: 3, latency_per_analysis: lat(55, 187), cost_total_usd: 2e-5, cost_per_case_usd: 6.67e-6, cost_per_analysis_usd: 6.67e-6,
  escalation_rate: rate(1, 3), abstention_rate: rate(1, 3), vision_abstention_rate: rate(0, 1), retrieval_success_rate: rate(1, 2), cache_hit_rate: rate(0, 1),
  weather_sources: { live: 1 }, model_disagreement_count: 0, decision_states: { PRELIMINARY_GUIDANCE: 2, EXPERT_REVIEW: 1 },
  notes: ["Only one vision model is deployed."],
} as Overview;
const routes: RoutesOut = {
  window: overview.window, total_analyses: 3,
  by_path: [{ path: "image_diagnosis", count: 1, share: 0.3333, avg_latency_ms: 55, avg_cost_usd: 2e-5, decision_states: { PRELIMINARY_GUIDANCE: 1 } }, { path: "treatment_safety", count: 1, share: 0.3333, avg_latency_ms: 0, avg_cost_usd: 0, decision_states: { EXPERT_REVIEW: 1 } }],
  by_intent: { crop_health_image: 1, weather_context: 1 }, by_decision_state: { PRELIMINARY_GUIDANCE: 2, EXPERT_REVIEW: 1 },
  vision_call_rate: rate(1, 3), skipped_steps: { weather: 2 }, estimated_cost_saved_usd: 4e-5,
} as RoutesOut;
const cost: CostLatencyOut = {
  window: overview.window, total_analyses: 3, latency_per_analysis: lat(55, 187), cost_total_usd: 2e-5, cost_per_analysis_usd: 6.67e-6, cost_per_case_usd: 6.67e-6,
  by_step: [{ step: "vision", tier: "vision_model", calls: 1, errors: 0, latency: { n: 1, p50_ms: 20, p95_ms: 20 }, total_cost_usd: 2e-5, avg_cost_usd: 2e-5 }],
  by_tier: [{ tier: "vision_model", description: "x", calls: 1, share_of_calls: 0.25, total_cost_usd: 2e-5, share_of_cost: 1 }],
  estimated_cost_saved_usd: 4e-5, cost_if_vision_always_ran_usd: 6e-5, notes: [],
} as CostLatencyOut;

const view = (days?: 7 | 30 | 90, locale: "en" | "mr" = "en") => render(<I18nProvider locale={locale}><MetricsDashboard days={days} /></I18nProvider>);

beforeEach(() => {
  api.metricsOverview.mockReset().mockResolvedValue(overview);
  api.metricsRoutes.mockReset().mockResolvedValue(routes);
  api.metricsCostLatency.mockReset().mockResolvedValue(cost);
});

describe("Metrics dashboard", () => {
  it("shows the headline numbers from the real fields, with the small-dollar rule", async () => {
    view();
    await screen.findByText("55 ms / 187 ms");
    expect(screen.getByText("$0.0000067")).toBeInTheDocument();
    expect(screen.getAllByText("33%").length).toBe(2);
    expect(screen.getByText("1 of 3 analyses")).toBeInTheDocument();
    expect(screen.getByText("Total $0.00002 · estimated, not billed")).toBeInTheDocument();
    expect(screen.getByText(/3 analyses from 3 cases/)).toBeInTheDocument();
    expect(screen.getByText("Only one vision model is deployed.")).toBeInTheDocument();
  });

  it("asks the API for the chosen window, and all time by default", async () => {
    view(30);
    await waitFor(() => expect(api.metricsOverview).toHaveBeenCalledWith(30));
    view();
    await waitFor(() => expect(api.metricsOverview).toHaveBeenCalledWith(undefined));
  });

  it("window pills are links, with the current one marked", async () => {
    view(7);
    await screen.findByText("55 ms / 187 ms");
    const nav = screen.getByRole("navigation", { name: "Time window" });
    expect(within(nav).getByRole("link", { name: "7 days" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "All time" })).toHaveAttribute("href", "/metrics");
    expect(within(nav).getByRole("link", { name: "30 days" })).toHaveAttribute("href", "/metrics?days=30");
  });

  it("lists all five decision states, zeros included, and the route table", async () => {
    view();
    const bar = (await screen.findAllByTestId("hbar")).map((b) => b.textContent ?? "").find((t) => t.includes("Needs a better photo")) ?? "";
    for (const part of ["Needs a better photo=0", "Needs more information=0", "Preliminary guidance=2", "With an expert=1", "Not supported=0"]) expect(bar).toContain(part);
    expect(screen.getByText("image_diagnosis")).toBeInTheDocument();
    expect(screen.getByText("Vision called in 1 of 3")).toBeInTheDocument();
  });

  it("lists all four tiers, with 'None yet' for any without calls, and the what-if cost", async () => {
    view();
    await screen.findByText("Large model");
    expect(screen.getAllByText("None yet")).toHaveLength(3); // small model, tool and large model had no calls in the fixture
    expect(screen.getByText("$0.00006")).toBeInTheDocument();
    expect(screen.getByText("vs $0.00002 actual")).toBeInTheDocument();
  });

  it("empty window: dashes instead of fake zeros for rates, and a way back to all time", async () => {
    api.metricsOverview.mockResolvedValue({ ...overview, total_analyses: 0, total_cases: 0, latency_per_analysis: { n: 0 }, cost_per_case_usd: null, cost_total_usd: 0, escalation_rate: rate(0, 0), abstention_rate: rate(0, 0), notes: [] });
    view(7);
    await screen.findByText("No analyses in this window");
    expect(screen.getByText("No analyses to time")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(2);
    expect(screen.getByRole("link", { name: "Show all time" })).toHaveAttribute("href", "/metrics");
    expect(screen.queryByText("Route distribution")).not.toBeInTheDocument();
  });

  it("one endpoint failing does not hide the others, and retry reloads", async () => {
    api.metricsRoutes.mockRejectedValueOnce({ code: "server" }).mockResolvedValue(routes);
    view();
    await screen.findByText("55 ms / 187 ms");
    await screen.findAllByText("Couldn't load these metrics");
    expect(screen.getByText("Cost and latency by step")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Try again" })[0]);
    await screen.findByText("image_diagnosis");
  });

  it("renders in Marathi with no raw keys", async () => {
    const { container } = view(undefined, "mr");
    await screen.findByText("ऑर्केस्ट्रेशन मेट्रिक्स");
    await screen.findByText("मार्गांचे वितरण");
    expect(container.textContent).not.toMatch(/\bm\.[a-z_.0-9]+/);
  });
});
