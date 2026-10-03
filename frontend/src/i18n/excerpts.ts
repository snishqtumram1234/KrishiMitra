import { EXCERPTS_MR } from "./excerpts-mr";
import type { Locale } from "./locales";

export type LocalExcerpt = { text: string; lang: "en" | "mr"; translated: boolean };

/** A source passage in the reader's language: the Marathi draft translation when one exists, else the English original. */
export function localExcerpt(original: string, locale: Locale): LocalExcerpt {
  const mr = locale === "mr" ? EXCERPTS_MR[original] : undefined;
  return mr ? { text: mr, lang: "mr", translated: true } : { text: original, lang: "en", translated: false };
}
