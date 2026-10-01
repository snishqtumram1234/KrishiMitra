/**
 * Pure helpers for the metrics dashboard: the time window, number formatting rules, and the small data reshaping the
 * API leaves to the client (all five decision states with zeros; the most common outcome of a route).
 */
import type { DecisionState } from "./api-types";
import { DECISION_STATES } from "./api-types";
import type { Locale } from "../i18n/locales";
import { formatNumber } from "../i18n/format";

export const WINDOWS = [7, 30, 90] as const;
export type WindowDays = (typeof WINDOWS)[number];

/** `?days=` in the URL: 7, 30 or 90, anything else (or nothing) means all time, which is the API's default. */
export function parseWindow(value: string | null | undefined): WindowDays | undefined {
  const n = Number(value);
  return (WINDOWS as readonly number[]).includes(n) ? (n as WindowDays) : undefined;
}

type Rate = { numerator: number; denominator: number; rate: number | null };

/** "33%". A rate with nothing to divide by is null and shows as a dash, never as 0%. */
export function percent(locale: Locale, rate: number | null | undefined): string {
  return rate == null ? "—" : `${formatNumber(locale, rate * 100, { maximumFractionDigits: 0 })}%`;
}

export const rateParts = (r: Rate | null | undefined) => ({ num: r?.numerator ?? 0, den: r?.denominator ?? 0 });

/**
 * Dollar amounts here are tiny estimates (for example 0.0000067), so they keep two significant digits instead of
 * rounding to cents: "$0", "$0.0000067", "$0.0042", "$1.25".
 */
export function usd(locale: Locale, value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  if (value === 0) return "$0";
  const digits = value >= 1 ? 2 : Math.min(10, Math.max(2, 1 - Math.floor(Math.log10(value))));
  return `$${formatNumber(locale, value, { minimumFractionDigits: 0, maximumFractionDigits: digits })}`;
}

export function ms(locale: Locale, value: number | null | undefined, digits = 0): string {
  return value == null ? "—" : `${formatNumber(locale, value, { maximumFractionDigits: digits })} ms`;
}

/** The API lists only the decision states that occurred; the dashboard shows all five, zeros included. */
export function allStates(byState: Record<string, number> | undefined): { state: DecisionState; count: number }[] {
  return DECISION_STATES.map((state) => ({ state, count: byState?.[state] ?? 0 }));
}

/** The decision state a route most often ended in (ties go to the first in the canonical order), or null for no data. */
export function dominantState(byState: Record<string, number> | undefined): DecisionState | null {
  let best: DecisionState | null = null;
  let max = 0;
  for (const { state, count } of allStates(byState)) {
    if (count > max) {
      best = state;
      max = count;
    }
  }
  return best;
}

export const TIERS = ["small_model", "vision_model", "tool", "large_model"] as const;
export type Tier = (typeof TIERS)[number];

/** Every tier in a fixed order, with zeros for a tier the API did not list (the large model, for now). */
export function allTiers<T extends { tier: string }>(rows: T[] | undefined): { tier: Tier; row: T | null }[] {
  return TIERS.map((tier) => ({ tier, row: rows?.find((r) => r.tier === tier) ?? null }));
}

export const isTier = (v: string): v is Tier => (TIERS as readonly string[]).includes(v);
