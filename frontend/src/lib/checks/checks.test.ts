import { describe, expect, it, vi } from "vitest";
import type { CaseOut, ImageOut } from "../api-types";
import { DISTRICTS, GROWTH_STAGES, LIMITS } from "./reference";
import { newProgress, stepsFor, submitCropCheck, SubmitFailure, type CropSubmission } from "./submit";
import { checkCropForm, checkImage, checkStartDate, checkText, sniffImageType, todayInIndia } from "./validate";

const bytes = (...b: number[]) => new Uint8Array([...b, ...new Array(Math.max(0, 12 - b.length)).fill(0)]);
const blob = (b: Uint8Array, extra = 0) => new Blob([b as BlobPart, new Uint8Array(extra)]);

describe("image checks", () => {
  it("recognises JPEG, PNG and WebP from the bytes", () => {
    expect(sniffImageType(bytes(0xff, 0xd8, 0xff, 0xe0))).toBe("JPEG");
    expect(sniffImageType(bytes(0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a))).toBe("PNG");
    expect(sniffImageType(bytes(0x52, 0x49, 0x46, 0x46, 0, 0, 0, 0, 0x57, 0x45, 0x42, 0x50))).toBe("WebP");
  });
  it("rejects other formats, even if they would be named .jpg", () => {
    expect(sniffImageType(bytes(0x47, 0x49, 0x46, 0x38))).toBeNull(); // GIF
    expect(sniffImageType(bytes(0x25, 0x50, 0x44, 0x46))).toBeNull(); // PDF
    expect(sniffImageType(bytes(0x52, 0x49, 0x46, 0x46, 0, 0, 0, 0, 0x57, 0x41, 0x56, 0x45))).toBeNull(); // WAV
  });
  it("checkImage reports empty, too large and wrong type, and accepts exactly 10 MB", async () => {
    expect(await checkImage(new Blob([]))).toEqual({ ok: false, problem: "empty" });
    expect(await checkImage(blob(bytes(0xff, 0xd8, 0xff), LIMITS.imageMaxBytes))).toEqual({ ok: false, problem: "tooLarge" });
    expect(await checkImage(blob(bytes(0x47, 0x49, 0x46, 0x38)))).toEqual({ ok: false, problem: "wrongType" });
    const exactly = new Blob([bytes(0xff, 0xd8, 0xff) as BlobPart, new Uint8Array(LIMITS.imageMaxBytes - 12)]);
    expect(exactly.size).toBe(LIMITS.imageMaxBytes);
    expect(await checkImage(exactly)).toEqual({ ok: true, type: "JPEG" });
  });
});

describe("date and text checks", () => {
  it("uses today's date in India, not UTC", () => {
    expect(todayInIndia(new Date("2026-09-30T20:30:00Z"))).toBe("2026-10-01"); // 02:00 IST next day
  });
  it("rejects future and malformed start dates, allows today and the past", () => {
    expect(checkStartDate("2026-10-02", "2026-10-01")).toBe("future");
    expect(checkStartDate("2026-10-01", "2026-10-01")).toBeNull();
    expect(checkStartDate("2026-09-01", "2026-10-01")).toBeNull();
    expect(checkStartDate("2026-02-30", "2026-10-01")).toBe("invalid");
    expect(checkStartDate("01-10-2026", "2026-10-01")).toBe("invalid");
    expect(checkStartDate("", "2026-10-01")).toBeNull();
  });
  it("checks required and maximum text length on the trimmed value", () => {
    expect(checkText("   ", 10, true)).toBe("required");
    expect(checkText("", 10, false)).toBeNull();
    expect(checkText("x".repeat(11), 10, false)).toBe("tooLong");
    expect(checkText(` ${"x".repeat(10)} `, 10, true)).toBeNull();
  });
  it("checkCropForm needs a valid photo and a description, and flags each bad field", () => {
    const ok = { description: "spots", startedAt: "", rainfall: "", more: "" };
    expect(checkCropForm(ok, true, "2026-10-01")).toEqual({});
    expect(checkCropForm(ok, false, "2026-10-01")).toEqual({ photo: "missing" });
    expect(
      checkCropForm({ description: "", startedAt: "2027-01-01", rainfall: "x".repeat(201), more: "x".repeat(2001) }, true, "2026-10-01"),
    ).toEqual({ describe: "required", started: "future", rain: "tooLong", more: "tooLong" });
  });
});

describe("reference data", () => {
  it("has the backend's 36 districts and no duplicates", () => {
    expect(DISTRICTS).toHaveLength(36);
    expect(new Set(DISTRICTS).size).toBe(36);
    expect(GROWTH_STAGES).toContain("R3");
  });
});

describe("submitCropCheck", () => {
  const submission = (field = false): CropSubmission => ({
    case: { crop: "soybean", district: "Pune", symptom_context: "spots", language: "en" },
    leaf: new Blob(["leaf"]),
    field: field ? new Blob(["field"]) : null,
  });
  const analysis = { case_id: "c1" } as never;

  function fakeApi() {
    return {
      createCase: vi.fn(async () => ({ id: "c1" }) as CaseOut),
      uploadImage: vi.fn(async () => ({}) as ImageOut),
      analyzeCase: vi.fn(async () => analysis),
    };
  }

  it("runs create, upload, analyse in order, with the field photo when given", async () => {
    const api = fakeApi();
    const steps: string[] = [];
    const out = await submitCropCheck(api as never, submission(true), newProgress(), (s) => steps.push(s));
    expect(out).toBe(analysis);
    expect(steps).toEqual(["details", "leaf", "field", "analyze"]);
    expect(api.uploadImage.mock.calls.map((c) => (c as unknown as [string, { kind: string }])[1].kind)).toEqual(["leaf_closeup", "field_overview"]);
    expect(stepsFor(submission(true))).toEqual(["details", "leaf", "field", "analyze"]);
    expect(stepsFor(submission(false))).toEqual(["details", "leaf", "analyze"]);
  });

  it("after an upload failure, retrying does not create a second case or re-upload the first photo", async () => {
    const api = fakeApi();
    api.uploadImage.mockRejectedValueOnce(new Error("network")).mockResolvedValue({} as ImageOut);
    const progress = newProgress();
    await expect(submitCropCheck(api as never, submission(), progress, () => undefined)).rejects.toMatchObject({ step: "leaf" });
    expect(progress.caseId).toBe("c1");
    await submitCropCheck(api as never, submission(), progress, () => undefined);
    expect(api.createCase).toHaveBeenCalledTimes(1);
    expect(api.uploadImage).toHaveBeenCalledTimes(2); // the failed one, then the retry
    expect(api.analyzeCase).toHaveBeenCalledTimes(1);
  });

  it("does not re-upload a photo that already succeeded when a later step fails", async () => {
    const api = fakeApi();
    api.analyzeCase.mockRejectedValueOnce(new Error("timeout"));
    const progress = newProgress();
    await expect(submitCropCheck(api as never, submission(true), progress, () => undefined)).rejects.toBeInstanceOf(SubmitFailure);
    await submitCropCheck(api as never, submission(true), progress, () => undefined);
    expect(api.uploadImage).toHaveBeenCalledTimes(2);
    expect(api.analyzeCase).toHaveBeenCalledTimes(2);
  });

  it("can continue without the field photo after it fails", async () => {
    const api = fakeApi();
    api.uploadImage.mockResolvedValueOnce({} as ImageOut).mockRejectedValueOnce(new Error("413"));
    const progress = newProgress();
    await expect(submitCropCheck(api as never, submission(true), progress, () => undefined)).rejects.toMatchObject({ step: "field" });
    progress.skipField = true;
    await expect(submitCropCheck(api as never, submission(true), progress, () => undefined)).resolves.toBe(analysis);
    expect(stepsFor(submission(true), progress)).toEqual(["details", "leaf", "analyze"]);
  });
});
