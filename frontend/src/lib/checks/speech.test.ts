import { describe, expect, it } from "vitest";
import { pickVoice, speechChunks } from "./speech";

const v = (lang: string, name: string) => ({ lang, name, localService: true });

describe("pickVoice", () => {
  it("uses a Marathi voice, preferring a natural one", () => {
    const voices = [v("en-US", "David"), v("mr-IN", "Marathi basic"), v("mr-IN", "Microsoft Aarohi Online (Natural)")];
    expect(pickVoice(voices, "mr")?.name).toMatch(/Aarohi/);
  });
  it("falls back to a Hindi voice for Marathi, and never to an English one", () => {
    expect(pickVoice([v("en-IN", "Ravi"), v("hi-IN", "Google हिन्दी")], "mr")?.lang).toBe("hi-IN");
    expect(pickVoice([v("en-IN", "Ravi"), v("en-US", "Zira")], "mr")).toBeNull();
  });
  it("prefers Indian English for English", () => {
    expect(pickVoice([v("en-US", "Zira"), v("en_IN", "Ravi")], "en")?.name).toBe("Ravi");
  });
});

describe("speechChunks", () => {
  it("splits at Marathi and English sentence ends", () => {
    expect(speechChunks("पहिले वाक्य. दुसरे वाक्य। तिसरे?")).toEqual(["पहिले वाक्य.", "दुसरे वाक्य।", "तिसरे?"]);
  });
  it("keeps every piece short", () => {
    const long = Array.from({ length: 80 }, (_, i) => `शब्द${i}`).join(" ");
    const parts = speechChunks(long, 60);
    expect(parts.every((p) => p.length <= 60)).toBe(true);
    expect(parts.join(" ")).toBe(long);
  });
});
