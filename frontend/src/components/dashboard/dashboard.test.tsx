// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "@/i18n/client";
import type { CaseOut, DecisionState, WeatherResult } from "@/lib/api-types";
import { Dashboard } from "./Dashboard";

const api = { listCases: vi.fn(), getWeather: vi.fn() };
vi.mock("@/lib/api-client", () => ({
  ApiError: class ApiError extends Error {
    constructor(readonly code: string) {
      super(code);
    }
  },
  getApiClient: () => api,
}));

const row = (id: string, text: string, state: DecisionState | null, district = "Pune"): CaseOut =>
  ({ id, symptom_context: text, district, growth_stage: "R3", decision_state: state, created_at: "2026-09-30T20:30:00Z" }) as CaseOut;

const live: WeatherResult = {
  available: true, source: "live", provider: "Open-Meteo", district: "Pune", observed_at: "2026-10-01T02:00:00+05:30", stale: false,
  temperature_c: 23, humidity_pct: 92, rain_next_24h_mm: 0.8, rain_probability_max_pct: 71, wind_speed_kmh: 0.8, summary: "x",
} as WeatherResult;

const view = (locale: "en" | "mr" = "en") => render(<I18nProvider locale={locale}><Dashboard /></I18nProvider>);

beforeEach(() => {
  api.listCases.mockReset();
  api.getWeather.mockReset().mockResolvedValue(live);
});

describe("Farmer dashboard", () => {
  it("lists checks with a badge for each of the five states and for a check that was never analysed", async () => {
    api.listCases.mockResolvedValue([
      row("1", "A", "NEEDS_BETTER_IMAGE"),
      row("2", "B", "NEEDS_MORE_CONTEXT"),
      row("3", "C", "PRELIMINARY_GUIDANCE"),
      row("4", "D", "EXPERT_REVIEW"),
      row("5", "E", "UNSUPPORTED"),
      row("6", "F", null),
    ]);
    view();
    await screen.findByText("Recent checks · 6");
    for (const badge of ["Needs photo", "Needs info", "Guidance ready", "With an expert", "Not supported", "Not checked yet"]) {
      expect(screen.getByText(badge)).toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name: /^A/ })).toHaveAttribute("href", "/checks/1");
  });

  it("asks for the weather of the newest check's district, and falls back to Pune with no checks", async () => {
    api.listCases.mockResolvedValue([row("1", "A", null, "Nashik")]);
    view();
    await waitFor(() => expect(api.getWeather).toHaveBeenCalledWith("Nashik"));
  });

  it("empty state: invites a first check, and the weather still shows", async () => {
    api.listCases.mockResolvedValue([]);
    view();
    await screen.findByText("No crop checks yet");
    expect(screen.getByRole("link", { name: "Start your first check" })).toHaveAttribute("href", "/checks/new");
    await waitFor(() => expect(api.getWeather).toHaveBeenCalledWith("Pune"));
    await screen.findByText("Temperature");
  });

  it("error state: says what failed, retries, and the weather is independent of it", async () => {
    api.listCases.mockRejectedValueOnce({ code: "network" }).mockResolvedValue([row("1", "A", null)]);
    view();
    await screen.findByText("Couldn't load your checks");
    expect(screen.getByRole("alert")).toHaveTextContent("Check your internet connection");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await screen.findByText("Recent checks · 1");
  });

  it("an old weather reading says so and shows no rain forecast", async () => {
    api.listCases.mockResolvedValue([]);
    api.getWeather.mockResolvedValue({ ...live, source: "cached", stale: true });
    view();
    await screen.findByText(/more than 6 hours old/);
    expect(screen.getByText("Old reading")).toBeInTheDocument();
    expect(screen.queryByText("Rain in the next 24 hours")).not.toBeInTheDocument();
    expect(screen.queryByText("Highest chance of rain")).not.toBeInTheDocument();
  });

  it("weather failure shows a retry and does not hide the checks", async () => {
    api.listCases.mockResolvedValue([row("1", "A", "EXPERT_REVIEW")]);
    api.getWeather.mockRejectedValue(new Error("down"));
    view();
    await screen.findByText("The weather couldn't be loaded right now.");
    expect(screen.getByText("Recent checks · 1")).toBeInTheDocument();
  });

  it("renders in Marathi with no raw keys", async () => {
    api.listCases.mockResolvedValue([row("1", "A", "PRELIMINARY_GUIDANCE")]);
    const { container } = view("mr");
    await screen.findByText("अलीकडच्या तपासण्या · 1");
    expect(container.textContent).not.toMatch(/\b(dashboard|state|weather|check)\.[A-Za-z_]+/);
  });
});
