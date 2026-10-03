"use client";

import { useI18n } from "@/i18n/client";
import { DEMO_SAMPLES, type DemoSample } from "@/lib/checks/demo";

/** A row of sample photos. Choosing one fills the form and runs the check (the form does the work). */
export function DemoPicker({
  busyId,
  disabled,
  onPick,
}: {
  busyId: string | null;
  disabled: boolean;
  onPick: (sample: DemoSample) => void;
}) {
  const { t } = useI18n();
  return (
    <section className="rounded-card border border-line bg-sunken p-4" aria-labelledby="demo-title">
      <h2 id="demo-title" className="text-lg font-bold">
        {t("check.demo.title")}
      </h2>
      <p className="mt-1 text-sm text-ink-muted">{t("check.demo.hint")}</p>
      <ul className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {DEMO_SAMPLES.map((sample) => {
          const name = t(`check.demo.${sample.id}.name`);
          return (
            <li key={sample.id}>
              <button
                type="button"
                disabled={disabled}
                aria-label={t("check.demo.use", { name })}
                onClick={() => onPick(sample)}
                className="group block w-full overflow-hidden rounded-control border border-control-border bg-surface text-start focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-60"
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- a small static sample photo from /public */}
                <img src={sample.photo} alt="" className="aspect-square w-full object-cover" loading="lazy" />
                <span className="block px-3 py-2 text-sm font-medium">
                  {busyId === sample.id ? t("check.demo.filling") : name}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-xs text-ink-muted">{t("check.demo.note")}</p>
    </section>
  );
}
