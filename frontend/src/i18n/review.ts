/**
 * Which Marathi strings a native speaker has reviewed.
 *
 * EVERY Marathi string is currently a draft. To mark one reviewed, add its key to REVIEWED_KEYS in the same commit
 * that applies the reviewer's corrections to mr.ts. `npm run i18n:review` writes the sheet to hand to the reviewer.
 */
import type { Locale } from "./locales";
import { en, type MessageKey } from "./messages/en";

export const REVIEWED_KEYS: ReadonlySet<MessageKey> = new Set<MessageKey>([]);

export const ALL_KEYS = Object.keys(en) as MessageKey[];

export function needsNativeReview(locale: Locale, key: MessageKey): boolean {
  return locale === "mr" && !REVIEWED_KEYS.has(key);
}

export function unreviewedKeys(): MessageKey[] {
  return ALL_KEYS.filter((k) => needsNativeReview("mr", k));
}

/** "Marathi draft: needs native review" is shown whenever the UI is Marathi, unless explicitly turned off. */
export function shouldShowDraftBadge(locale: Locale, flag: string | undefined): boolean {
  return locale === "mr" && flag !== "false" && unreviewedKeys().length > 0;
}

export const DRAFT_BADGE_TEXT = "Marathi draft: needs native review";
