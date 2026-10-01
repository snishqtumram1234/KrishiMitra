/**
 * Client-side checks that mirror what the API enforces, so a farmer hears about a problem before a slow upload.
 * The server stays the authority (it sniffs the file bytes and answers 413 / 415 / 422); these only save a round trip.
 */
import { LIMITS } from "./reference";

export type ImageProblem = "empty" | "tooLarge" | "wrongType";
export type ImageCheck = { ok: true; type: "JPEG" | "PNG" | "WebP" } | { ok: false; problem: ImageProblem };

const startsWith = (bytes: Uint8Array, signature: number[], offset = 0) =>
  signature.every((b, i) => bytes[offset + i] === b);

/** Names the image format from its first bytes (not from the file name or the browser's guess), or null. */
export function sniffImageType(bytes: Uint8Array): "JPEG" | "PNG" | "WebP" | null {
  if (startsWith(bytes, [0xff, 0xd8, 0xff])) return "JPEG";
  if (startsWith(bytes, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) return "PNG";
  if (startsWith(bytes, [0x52, 0x49, 0x46, 0x46]) && startsWith(bytes, [0x57, 0x45, 0x42, 0x50], 8)) return "WebP";
  return null;
}

export async function checkImage(file: Blob): Promise<ImageCheck> {
  if (file.size === 0) return { ok: false, problem: "empty" };
  if (file.size > LIMITS.imageMaxBytes) return { ok: false, problem: "tooLarge" };
  const head = new Uint8Array(await file.slice(0, 12).arrayBuffer());
  const type = sniffImageType(head);
  return type ? { ok: true, type } : { ok: false, problem: "wrongType" };
}

/** Today's date in India (YYYY-MM-DD). Farmers think in local dates, and a date the farmer enters must not be "tomorrow". */
export function todayInIndia(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
}

export type DateProblem = "invalid" | "future";
export function checkStartDate(value: string, today: string = todayInIndia()): DateProblem | null {
  if (!value) return null;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return "invalid";
  const d = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(d.getTime()) || d.toISOString().slice(0, 10) !== value) return "invalid";
  return value > today ? "future" : null;
}

export type TextProblem = "required" | "tooLong";
export function checkText(value: string, max: number, required: boolean): TextProblem | null {
  const v = value.trim();
  if (required && v.length === 0) return "required";
  return v.length > max ? "tooLong" : null;
}

export type CropFormValues = {
  description: string; // what's happening: becomes `symptom_context`
  startedAt: string;
  rainfall: string;
  more: string; // "anything else you noticed": becomes `description`
};
export type CropFormField = "photo" | "describe" | "started" | "rain" | "more";
export type CropFormProblems = Partial<Record<CropFormField, string>>;

/** Which fields of the crop form are wrong. Values are problem names, mapped to dictionary text by the form. */
export function checkCropForm(values: CropFormValues, hasValidPhoto: boolean, today?: string): CropFormProblems {
  const problems: CropFormProblems = {};
  if (!hasValidPhoto) problems.photo = "missing";
  const describe = checkText(values.description, LIMITS.textMax, true);
  if (describe) problems.describe = describe;
  const started = checkStartDate(values.startedAt, today);
  if (started) problems.started = started;
  const rain = checkText(values.rainfall, LIMITS.rainfallMax, false);
  if (rain) problems.rain = rain;
  const more = checkText(values.more, LIMITS.textMax, false);
  if (more) problems.more = more;
  return problems;
}
