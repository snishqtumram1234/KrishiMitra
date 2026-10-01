import { describe, expect, it } from "vitest";
import {
  CONFIDENCE_BANDS,
  DECISION_STATES,
  MISSING_INFORMATION_CODES,
  QUALITY_ISSUES,
  REASON_CODES,
  TRACE_STEP_IDS,
} from "@/lib/api-types";
import { apiErrorText, bandAria, reasonCopy, stateCopy } from "./copy";
import { formatDate, formatDateTime } from "./format";
import { localeFromAcceptLanguage } from "./locales";
import { en } from "./messages/en";
import { mr } from "./messages/mr";
import { DRAFT_BADGE_TEXT, needsNativeReview, shouldShowDraftBadge, unreviewedKeys } from "./review";
import { MESSAGES, createTranslator, interpolate, placeholdersOf, type MessageKey } from "./translate";

const keys = Object.keys(en) as MessageKey[];

describe("dictionaries", () => {
  it("Marathi has exactly the English keys", () => {
    expect(Object.keys(mr).sort()).toEqual([...keys].sort());
  });
  it("every Marathi string is filled in and uses the same placeholders as English", () => {
    for (const key of keys) {
      expect(mr[key].trim(), key).not.toBe("");
      expect(placeholdersOf(mr[key]).sort(), key).toEqual(placeholdersOf(en[key]).sort());
    }
  });
  it("no string names a pesticide or gives a dose", () => {
    const risky = /\b(mg|ml|kg|gm|litre|liter|per acre|mancozeb|chlorpyrifos|tebuconazole|propiconazole)\b/i;
    for (const locale of ["en", "mr"] as const) {
      for (const key of keys) expect(MESSAGES[locale][key], key).not.toMatch(risky);
    }
  });
  it("English only mentions a confirmed diagnosis to deny it", () => {
    for (const key of keys) {
      const text = en[key];
      if (/confirmed diagnosis/i.test(text)) expect(text, key).toMatch(/(not|never) an? (lab-)?confirmed diagnosis/i);
    }
  });
});

describe("interpolate", () => {
  it("fills placeholders and throws on a missing one outside production", () => {
    expect(interpolate("Hi {name}", { name: "A" })).toBe("Hi A");
    expect(() => interpolate("Hi {name}")).toThrow(/name/);
  });
});

describe("copy built from structured fields covers every API value", () => {
  const t = createTranslator("en");
  it("states, reasons, bands, missing info, issues and trace steps all resolve to real text", () => {
    for (const s of DECISION_STATES) expect(stateCopy(t, s).label).toBeTruthy();
    for (const r of REASON_CODES) {
      const c = reasonCopy(t, r, r === "quality_failed" ? "blurry" : "advisory", { district: "Pune" });
      expect(c.title && c.body, r).toBeTruthy();
    }
    for (const b of CONFIDENCE_BANDS) expect(bandAria(t, b)).toContain(t(`band.${b}.label`));
    for (const m of MISSING_INFORMATION_CODES) expect(t(`missing.${m}.title`)).toBeTruthy();
    for (const q of QUALITY_ISSUES) expect(t(`quality.issue.${q}`)).toBeTruthy();
    for (const s of TRACE_STEP_IDS) expect(t(`trace.step.${s}`)).toBeTruthy();
  });
  it("quality_failed folds the specific tip into the body", () => {
    expect(reasonCopy(t, "quality_failed", "blurry").body).toContain("blurry");
  });
  it("an unknown source failure falls back instead of showing a raw key", () => {
    expect(reasonCopy(t, "sources_unavailable", "brand_new_failure").body).toBe(
      en["reason.sources_unavailable.unknown"],
    );
  });
  it("API errors are shown from their code, never from server text", () => {
    expect(apiErrorText(t, "network")).toBe(en["error.network"]);
  });
});

describe("Marathi review tracking", () => {
  it("flags every Marathi key as unreviewed and none of English", () => {
    expect(unreviewedKeys().length).toBe(keys.length);
    expect(needsNativeReview("mr", "app.name")).toBe(true);
    expect(needsNativeReview("en", "app.name")).toBe(false);
  });
  it("shows the draft badge for Marathi unless switched off", () => {
    expect(shouldShowDraftBadge("mr", undefined)).toBe(true);
    expect(shouldShowDraftBadge("mr", "false")).toBe(false);
    expect(shouldShowDraftBadge("en", undefined)).toBe(false);
    expect(DRAFT_BADGE_TEXT).toBe("Marathi draft: needs native review");
  });
});

describe("locale and formatting", () => {
  it("picks the first supported language by preference", () => {
    expect(localeFromAcceptLanguage("hi;q=0.9, mr-IN;q=0.8, en;q=0.5")).toBe("mr");
    expect(localeFromAcceptLanguage("fr")).toBeNull();
  });
  it("formats times in IST", () => {
    expect(formatDateTime("en", "2026-09-30T20:30:00Z")).toMatch(/01 Oct 2026, 02:00 IST/);
    expect(formatDateTime("en", "nonsense")).toBe("");
    expect(formatDate("en", "2026-09-25")).toBe("25 Sep 2026");
    expect(formatDate("en", "2026-10-01")).toBe("01 Oct 2026");
  });
});
