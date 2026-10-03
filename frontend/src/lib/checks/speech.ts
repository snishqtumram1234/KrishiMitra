/**
 * Read-aloud helpers for the result page (the browser's own speech synthesis; nothing is sent anywhere).
 *
 * Marathi: browsers name the language "mr-IN" but many devices have no Marathi voice; asking for "mr-IN" without one makes
 * the browser read Devanagari with an English voice. So pick a Marathi voice, else a Hindi one (it reads Devanagari
 * correctly), else report that there is none. Long text is spoken sentence by sentence because some browsers stop
 * speaking a single long utterance after about 15 seconds.
 */
export type VoiceLike = Pick<SpeechSynthesisVoice, "lang" | "name" | "localService">;

export function pickVoice<V extends VoiceLike>(voices: readonly V[], locale: "en" | "mr"): V | null {
  const by = (prefix: string) => voices.filter((v) => v.lang.toLowerCase().replace("_", "-").startsWith(prefix));
  // natural/online voices sound far better; prefer them when present
  const best = (list: V[]) => list.find((v) => /natural|online|google/i.test(v.name)) ?? list[0] ?? null;
  if (locale === "mr") return best(by("mr")) ?? best(by("hi"));
  return best(by("en-in")) ?? best(by("en"));
}

/** Splits text into pieces of at most `max` characters, at sentence ends (".", "।", "?", "!") where possible. */
export function speechChunks(text: string, max = 180): string[] {
  const sentences = text.replace(/\s+/g, " ").match(/[^.।?!]+[.।?!]*/g) ?? [];
  const out: string[] = [];
  for (const raw of sentences) {
    const s = raw.trim();
    if (!s) continue;
    if (s.length <= max) {
      out.push(s);
      continue;
    }
    let cur = "";
    for (const word of s.split(" ")) {
      if (cur && (cur + " " + word).length > max) {
        out.push(cur);
        cur = word;
      } else cur = cur ? `${cur} ${word}` : word;
    }
    if (cur) out.push(cur);
  }
  return out;
}

/** The voices list loads asynchronously in Chrome; wait for it once (up to 1.5 s). */
export function loadVoices(synth: SpeechSynthesis): Promise<SpeechSynthesisVoice[]> {
  const now = synth.getVoices();
  if (now.length) return Promise.resolve(now);
  return new Promise((resolve) => {
    const done = () => resolve(synth.getVoices());
    synth.addEventListener("voiceschanged", done, { once: true });
    setTimeout(done, 1500);
  });
}
