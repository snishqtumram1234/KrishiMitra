import { describe, expect, it } from "vitest";
import { allStates, allTiers, dominantState, ms, parseWindow, percent, usd } from "./metrics";

describe("window", () => {
  it("accepts 7, 30 and 90 days; anything else is all time", () => {
    expect(parseWindow("7")).toBe(7);
    expect(parseWindow("30")).toBe(30);
    expect(parseWindow("90")).toBe(90);
    for (const v of [undefined, null, "", "all", "365", "-1", "7.5", "abc"]) expect(parseWindow(v)).toBeUndefined();
  });
});

describe("number formatting", () => {
  it("a rate with no data is a dash, not 0%", () => {
    expect(percent("en", null)).toBe("—");
    expect(percent("en", 0)).toBe("0%");
    expect(percent("en", 0.3333)).toBe("33%");
    expect(percent("en", 1)).toBe("100%");
  });
  it("keeps two significant digits for tiny dollar estimates", () => {
    expect(usd("en", 0)).toBe("$0");
    expect(usd("en", 6.67e-6)).toBe("$0.0000067");
    expect(usd("en", 2e-5)).toBe("$0.00002");
    expect(usd("en", 0.0042)).toBe("$0.0042");
    expect(usd("en", 1.256)).toBe("$1.26");
    expect(usd("en", null)).toBe("—");
  });
  it("formats milliseconds and treats missing as a dash", () => {
    expect(ms("en", 55)).toBe("55 ms");
    expect(ms("en", 80.67, 1)).toBe("80.7 ms");
    expect(ms("en", null)).toBe("—");
  });
});

describe("reshaping", () => {
  it("lists all five decision states with zeros", () => {
    expect(allStates({ PRELIMINARY_GUIDANCE: 2, EXPERT_REVIEW: 1 })).toEqual([
      { state: "NEEDS_BETTER_IMAGE", count: 0 },
      { state: "NEEDS_MORE_CONTEXT", count: 0 },
      { state: "PRELIMINARY_GUIDANCE", count: 2 },
      { state: "EXPERT_REVIEW", count: 1 },
      { state: "UNSUPPORTED", count: 0 },
    ]);
    expect(allStates(undefined).every((s) => s.count === 0)).toBe(true);
  });
  it("finds the most common outcome of a route, or null with no data", () => {
    expect(dominantState({ EXPERT_REVIEW: 3, PRELIMINARY_GUIDANCE: 1 })).toBe("EXPERT_REVIEW");
    expect(dominantState({})).toBeNull();
  });
  it("always lists the four tiers, with null for one the API left out", () => {
    const t = allTiers([{ tier: "tool", calls: 2 }]);
    expect(t.map((x) => x.tier)).toEqual(["small_model", "vision_model", "tool", "large_model"]);
    expect(t.find((x) => x.tier === "large_model")?.row).toBeNull();
    expect(t.find((x) => x.tier === "tool")?.row).toEqual({ tier: "tool", calls: 2 });
  });
});
