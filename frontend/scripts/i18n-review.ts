/**
 * Writes the Marathi review sheet: every string that is not yet in REVIEWED_KEYS, with the English beside it.
 * Run: npm run i18n:review   (prints a markdown table to stdout; redirect it to a file to hand to the reviewer)
 */
import { en } from "../src/i18n/messages/en";
import { mr } from "../src/i18n/messages/mr";
import { unreviewedKeys } from "../src/i18n/review";

const cell = (s: string) => s.replace(/\|/g, "\|").replace(/\n/g, " ");
const keys = unreviewedKeys();
console.log(`# Marathi strings needing native review (${keys.length})\n`);
console.log("| Key | English | Marathi draft | Corrected Marathi |\n|---|---|---|---|");
for (const key of keys) console.log(`| ${key} | ${cell(en[key])} | ${cell(mr[key])} | |`);
