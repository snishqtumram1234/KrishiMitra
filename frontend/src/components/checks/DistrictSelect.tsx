"use client";

import { useI18n } from "@/i18n/client";
import { DISTRICTS } from "@/lib/checks/reference";
import { inputClass } from "./fields";

/** District list in the reader's language. The value sent to the API is always the English name. */
export function DistrictSelect({ id, value, onChange }: { id: string; value: string; onChange: (v: string) => void }) {
  const { t, locale } = useI18n();
  const label = (name: (typeof DISTRICTS)[number]) => t(`district.${name}`);
  const sorted = [...DISTRICTS].sort((a, b) => label(a).localeCompare(label(b), locale === "mr" ? "mr-IN" : "en-IN"));
  return (
    <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={inputClass(false)}>
      {sorted.map((name) => (
        <option key={name} value={name}>
          {label(name)}
        </option>
      ))}
    </select>
  );
}
