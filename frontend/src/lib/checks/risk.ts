/**
 * Weather conditions that verified advisory sources link to faster spread of a condition. Numbers are copied from the
 * source (never estimated), with the page, so the result screen can compare them with today's real district weather.
 *
 * Only conditions whose source gives numbers are listed. Rust: ICAR-IISR Extension Bulletin 18 (Revised Edition 2023),
 * PDF page 53: "low temperature (22-27 degree celcius) and high humidity (80-90%) keeps the leaf surface moist/wet".
 */
import type { WeatherResult } from "../api-types";

export type SpreadConditions = { tempMin: number; tempMax: number; humidityMin: number; page: number };

export const SPREAD_CONDITIONS: Partial<Record<string, SpreadConditions>> = {
  rust_like: { tempMin: 22, tempMax: 27, humidityMin: 80, page: 53 },
};

export type RiskVerdict = "favourable" | "notFavourable" | "unknown";

/**
 * Do today's conditions match the ones the source links to spread? Unknown when the weather is unavailable, stale (an old
 * reading is never used for crop advice) or missing a value.
 */
export function spreadRisk(weather: WeatherResult | null | undefined, c: SpreadConditions): RiskVerdict {
  if (!weather || !weather.available || weather.stale) return "unknown";
  const temp = weather.temperature_c;
  const humidity = weather.humidity_pct;
  if (temp == null || humidity == null) return "unknown";
  return temp >= c.tempMin && temp <= c.tempMax && humidity >= c.humidityMin ? "favourable" : "notFavourable";
}

/** The text read aloud or shared: the result's own words, in order, with nothing added. */
export function summaryText(parts: (string | null | undefined)[]): string {
  return parts
    .map((p) => (p ?? "").trim())
    .filter(Boolean)
    .join("\n\n");
}
