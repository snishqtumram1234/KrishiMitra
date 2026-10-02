"use client";

import { useEffect, useState } from "react";
import { growthStageText } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { formatDateTime, formatNumber } from "@/i18n/format";
import { getApiClient } from "@/lib/api-client";
import type { CaseOut, WeatherResult } from "@/lib/api-types";
import { spreadRisk, type SpreadConditions } from "@/lib/checks/risk";

/** Official contacts (checked against government sources): the national toll-free farmer helpline and the KVK portal. */
export const KISAN_CALL_CENTRE = "1800-180-1551";
export const KVK_PORTAL = "https://kvk.icar.gov.in/";

const chip = "inline-flex items-center rounded-control bg-surface px-2.5 py-1 text-sm";

// ---------------------------------------------------------------- report header
export function ReportHeader({ caseId, createdAt, item }: { caseId: string; createdAt: string; item: CaseOut | null }) {
  const { t, locale } = useI18n();
  return (
    <header className="space-y-2">
      <p className="eyebrow">{t("report.title")}</p>
      <div className="flex flex-wrap gap-2 text-ink-muted">
        <span className={chip}>{t("report.case", { id: caseId.slice(0, 8).toUpperCase() })}</span>
        <span className={chip}>{formatDateTime(locale, createdAt)}</span>
        <span className={chip}>{t("check.crop.soybean")}</span>
        {item?.district && <span className={chip}>{item.district}</span>}
        {item?.growth_stage && <span className={chip}>{growthStageText(t, item.growth_stage)}</span>}
      </div>
      {item?.symptom_context && (
        <p className="text-ink-muted">
          <span className="font-medium text-ink">{t("result.question")}: </span>
          <span dir="auto">{item.symptom_context}</span>
        </p>
      )}
    </header>
  );
}

// ---------------------------------------------------------------- listen / share / save
export function ActionBar({ text }: { text: string }) {
  const { t, locale } = useI18n();
  const [speaking, setSpeaking] = useState(false);
  const canSpeak = typeof window !== "undefined" && "speechSynthesis" in window;

  useEffect(() => () => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
  }, []);

  function listen() {
    const synth = window.speechSynthesis;
    if (speaking) {
      synth.cancel();
      setSpeaking(false);
      return;
    }
    const u = new SpeechSynthesisUtterance(text);
    u.lang = locale === "mr" ? "mr-IN" : "en-IN";
    u.rate = 0.95;
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    synth.cancel();
    synth.speak(u);
    setSpeaking(true);
  }

  async function share() {
    const message = `${t("report.shareIntro")}\n\n${text}`;
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({ title: t("report.title"), text: message });
        return;
      } catch {
        // the farmer closed the share sheet: nothing to do
        return;
      }
    }
    window.open(`https://wa.me/?text=${encodeURIComponent(message)}`, "_blank", "noopener,noreferrer");
  }

  const button = "inline-flex min-h-11 items-center gap-2 rounded-control border border-control-border bg-surface px-4 font-medium";
  return (
    <div className="flex flex-wrap gap-2 print:hidden">
      {canSpeak && (
        <button type="button" onClick={listen} aria-pressed={speaking} className={button}>
          <span aria-hidden="true">{speaking ? "■" : "▶"}</span>
          {speaking ? t("report.stop") : t("report.listen")}
        </button>
      )}
      <button type="button" onClick={() => void share()} className={button}>
        <span aria-hidden="true">↗</span>
        {t("report.share")}
      </button>
      <button type="button" onClick={() => window.print()} className={button}>
        <span aria-hidden="true">⎙</span>
        {t("report.print")}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------- weather risk (only where the source gives numbers)
export function WeatherRisk({
  district,
  conditions,
  sourceTitle,
}: {
  district: string;
  conditions: SpreadConditions;
  sourceTitle: string;
}) {
  const { t, locale } = useI18n();
  const [weather, setWeather] = useState<WeatherResult | null | "failed">(null);

  useEffect(() => {
    let current = true;
    getApiClient().getWeather(district).then(
      (w) => current && setWeather(w),
      () => current && setWeather("failed"),
    );
    return () => {
      current = false;
    };
  }, [district]);

  if (weather === null) return null;
  const w = weather === "failed" ? null : weather;
  const verdict = spreadRisk(w, conditions);
  if (verdict === "unknown" || !w) return null; // no live, fresh reading: say nothing rather than guess

  const n = (v: number) => formatNumber(locale, v, { maximumFractionDigits: 0 });
  const favourable = verdict === "favourable";
  return (
    <section className={`rounded-card border p-5 sm:p-6 ${favourable ? "border-warning-accent bg-warning-bg" : "border-line bg-surface"}`}>
      <p className="eyebrow">{t("risk.title", { district })}</p>
      <p className={`mt-2 text-xl font-bold ${favourable ? "text-warning-fg" : ""}`}>
        {favourable ? t("risk.favourable") : t("risk.notFavourable")}
      </p>
      <p className="mt-2">
        {t("risk.now", { temp: n(w.temperature_c ?? 0), humidity: n(w.humidity_pct ?? 0) })}{" "}
        {t("risk.source", { tmin: n(conditions.tempMin), tmax: n(conditions.tempMax), hmin: n(conditions.humidityMin) })}
      </p>
      {favourable && <p className="mt-2 font-medium">{t("risk.watch")}</p>}
      <p className="mt-3 text-sm text-ink-muted">
        {t("risk.provenance", { provider: w.provider ?? "Open-Meteo", title: sourceTitle, page: n(conditions.page) })}
      </p>
    </section>
  );
}

// ---------------------------------------------------------------- help
export function HelpCard() {
  const { t } = useI18n();
  return (
    <section className="rounded-card border border-line bg-surface p-5 sm:p-6">
      <p className="eyebrow">{t("help.title")}</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <a href={`tel:${KISAN_CALL_CENTRE.replace(/-/g, "")}`} className="block rounded-card border border-control-border p-4 no-underline hover:bg-brand-wash">
          <span className="block font-bold text-ink">{t("help.kcc.title")}</span>
          <span className="mt-1 block text-2xl font-bold text-brand">{KISAN_CALL_CENTRE}</span>
          <span className="mt-1 block text-sm text-ink-muted">{t("help.kcc.body")}</span>
        </a>
        <a href={KVK_PORTAL} target="_blank" rel="noopener noreferrer" className="block rounded-card border border-control-border p-4 no-underline hover:bg-brand-wash">
          <span className="block font-bold text-ink">{t("help.kvk.title")}</span>
          <span className="mt-1 block text-brand underline">kvk.icar.gov.in</span>
          <span className="mt-1 block text-sm text-ink-muted">{t("help.kvk.body")}</span>
        </a>
      </div>
    </section>
  );
}
