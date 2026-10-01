"use client";

import { useTransition } from "react";
import { setLocale } from "@/actions/locale";
import { useI18n } from "@/i18n/client";
import { LOCALES, LOCALE_NAMES } from "@/i18n/locales";

export function LanguageToggle() {
  const { locale, t } = useI18n();
  const [pending, startTransition] = useTransition();
  return (
    <div role="group" aria-label={t("language.choose")} className="inline-flex rounded-control border border-control-border">
      {LOCALES.map((code) => (
        <button
          key={code}
          type="button"
          lang={code}
          aria-pressed={locale === code}
          disabled={pending}
          onClick={() => locale !== code && startTransition(() => setLocale(code))}
          className={`min-h-11 px-3 text-sm font-medium first:rounded-l-control last:rounded-r-control ${
            locale === code ? "bg-brand text-white" : "bg-surface text-ink"
          }`}
        >
          {LOCALE_NAMES[code]}
        </button>
      ))}
    </div>
  );
}
