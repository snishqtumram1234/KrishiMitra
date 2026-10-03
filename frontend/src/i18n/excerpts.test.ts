import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { splitPractices } from "@/components/result/ResultView";
import { EXCERPTS_MR } from "./excerpts-mr";
import { localExcerpt } from "./excerpts";

const passages: { excerpt: string; kind: string }[] = JSON.parse(
  readFileSync(join(process.cwd(), "..", "data", "advisories", "excerpts.json"), "utf-8"),
);

describe("Marathi source passages", () => {
  it("every source passage has a Marathi translation, with the same numbered steps", () => {
    for (const p of passages) {
      const mr = EXCERPTS_MR[p.excerpt];
      expect(mr, p.excerpt.slice(0, 50)).toBeTruthy();
      expect(splitPractices(mr).length, p.excerpt.slice(0, 50)).toBe(splitPractices(p.excerpt).length);
      expect(mr).toMatch(/[ऀ-ॿ]/);
    }
  });

  it("no stale translations for passages that no longer exist", () => {
    const current = new Set(passages.map((p) => p.excerpt));
    expect(Object.keys(EXCERPTS_MR).filter((k) => !current.has(k))).toEqual([]);
  });

  it("English readers get the original; unknown passages fall back to English", () => {
    const one = passages[0].excerpt;
    expect(localExcerpt(one, "en")).toEqual({ text: one, lang: "en", translated: false });
    expect(localExcerpt(one, "mr").translated).toBe(true);
    expect(localExcerpt("not a known passage", "mr")).toEqual({ text: "not a known passage", lang: "en", translated: false });
  });
});
