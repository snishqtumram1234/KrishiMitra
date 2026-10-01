import type { Locale } from "./locales";

const INTL_LOCALE: Record<Locale, string> = { en: "en-IN", mr: "mr-IN" };
/** All times are shown in Indian Standard Time, the farmers' time zone. */
export const DISPLAY_TIME_ZONE = "Asia/Kolkata";
/**
 * OPEN DECISION (design-handoff/README.md "Still open"): digits inside Marathi text. "latn" = 0-9 (used everywhere
 * today). Change to "deva" for ०-९ once a Marathi reviewer decides; this one constant switches every date and number.
 */
export const NUMBERING_SYSTEM = "latn";

function toDate(value: string | number | Date): Date | null {
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "01 Oct 2026, 02:00 IST". Returns "" for an unparseable value rather than "Invalid Date". */
export function formatDateTime(locale: Locale, value: string | number | Date | null | undefined): string {
  const d = value == null ? null : toDate(value);
  if (!d) return "";
  const text = new Intl.DateTimeFormat(INTL_LOCALE[locale], {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: DISPLAY_TIME_ZONE,
    numberingSystem: NUMBERING_SYSTEM,
  }).format(d);
  return `${text} IST`;
}

/** "01 Oct 2026". Dates without a time (published_at, symptom_started_at) are shown as written, not shifted by zone. */
export function formatDate(locale: Locale, value: string | null | undefined): string {
  if (!value) return "";
  const d = toDate(value.length === 10 ? `${value}T00:00:00Z` : value);
  if (!d) return "";
  return new Intl.DateTimeFormat(INTL_LOCALE[locale], {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: value.length === 10 ? "UTC" : DISPLAY_TIME_ZONE,
    numberingSystem: NUMBERING_SYSTEM,
  }).format(d);
}

export function formatNumber(locale: Locale, value: number, options?: Intl.NumberFormatOptions): string {
  return new Intl.NumberFormat(INTL_LOCALE[locale], { numberingSystem: NUMBERING_SYSTEM, ...options }).format(value);
}
