import { describe, expect, it } from "vitest";
import type { WeatherResult } from "../api-types";
import { SPREAD_CONDITIONS, spreadRisk, summaryText } from "./risk";

const rust = SPREAD_CONDITIONS.rust_like!;
const w = (o: Partial<WeatherResult>): WeatherResult =>
  ({ available: true, source: "live", stale: false, temperature_c: 24, humidity_pct: 85, summary: "", ...o }) as WeatherResult;

describe("spreadRisk", () => {
  it("uses the numbers from the source (ICAR-IISR, page 53)", () => {
    expect(rust).toEqual({ tempMin: 22, tempMax: 27, humidityMin: 80, page: 53 });
  });
  it("is favourable only inside the source's temperature range with enough humidity", () => {
    expect(spreadRisk(w({}), rust)).toBe("favourable");
    expect(spreadRisk(w({ temperature_c: 22 }), rust)).toBe("favourable");
    expect(spreadRisk(w({ temperature_c: 30 }), rust)).toBe("notFavourable");
    expect(spreadRisk(w({ humidity_pct: 60 }), rust)).toBe("notFavourable");
  });
  it("never judges from missing, unavailable or old weather", () => {
    expect(spreadRisk(null, rust)).toBe("unknown");
    expect(spreadRisk(w({ available: false }), rust)).toBe("unknown");
    expect(spreadRisk(w({ stale: true }), rust)).toBe("unknown");
    expect(spreadRisk(w({ humidity_pct: null }), rust)).toBe("unknown");
  });
  it("lists no conditions where the source gives no numbers", () => {
    expect(SPREAD_CONDITIONS.insect_damage).toBeUndefined();
    expect(SPREAD_CONDITIONS.leaf_spot_like).toBeUndefined();
  });
});

describe("summaryText", () => {
  it("keeps the result's own words in order and drops empty parts", () => {
    expect(summaryText(["A", null, " ", "B"])).toBe(["A", "B"].join(String.fromCharCode(10, 10)));
  });
});
