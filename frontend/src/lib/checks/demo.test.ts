import { existsSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { MESSAGES } from "@/i18n/translate";
import { GROWTH_STAGES, LIMITS } from "./reference";
import { DEMO_SAMPLES, daysBefore } from "./demo";
import { checkCropForm, todayInIndia } from "./validate";

describe("daysBefore", () => {
  it("counts back across month and year ends", () => {
    expect(daysBefore("2026-10-03", 6)).toBe("2026-09-27");
    expect(daysBefore("2026-01-02", 4)).toBe("2025-12-29");
  });
});

describe("demo samples", () => {
  it("each has a photo file, a real growth stage and its text in both languages", () => {
    for (const s of DEMO_SAMPLES) {
      expect(existsSync(join(process.cwd(), "public", s.photo)), s.photo).toBe(true);
      expect(GROWTH_STAGES as readonly string[]).toContain(s.stage);
      for (const locale of ["en", "mr"] as const) {
        for (const part of ["name", "describe", "rain", "more"] as const) {
          const text = MESSAGES[locale][`check.demo.${s.id}.${part}` as const];
          expect(text, `${locale} ${s.id}.${part}`).toBeTruthy();
        }
      }
    }
  });

  it("fills a form that passes the form's own checks", () => {
    const today = todayInIndia();
    for (const s of DEMO_SAMPLES) {
      for (const locale of ["en", "mr"] as const) {
        const m = MESSAGES[locale];
        const problems = checkCropForm(
          {
            description: m[`check.demo.${s.id}.describe` as const],
            startedAt: daysBefore(today, s.daysAgo),
            rainfall: m[`check.demo.${s.id}.rain` as const],
            more: m[`check.demo.${s.id}.more` as const],
          },
          true,
          today,
        );
        expect(problems, `${locale} ${s.id}`).toEqual({});
      }
    }
    expect(LIMITS.rainfallMax).toBeGreaterThan(40);
  });
});
