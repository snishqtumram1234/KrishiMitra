"use client";

import { useEffect, useState } from "react";
import { bandAria, bandExplanation, bandLabel, categoryLabel, growthStageText, isQualityIssue, missingCopy, qualityIssueText } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { formatDate, formatDateTime, formatNumber } from "@/i18n/format";
import { getApiClient } from "@/lib/api-client";
import type { AdvisorySource, CaseAnalysisOut, CaseOut, ConfidenceBand, MissingInformationCode, WeatherResult } from "@/lib/api-types";
import { MISSING_INFORMATION_CODES } from "@/lib/api-types";
import { BAND_THRESHOLDS, bandMarkerPercent, publishedDate, safeSourceUrl, sourceKind, stepOf, timelineRows } from "@/lib/checks/result";
import { weatherSourceLabel } from "@/i18n/copy";

/** The backend treats a saved weather reading as stale after this many hours (WEATHER_CACHE_MAX_AGE_HOURS). */
const WEATHER_STALE_HOURS = 6;
const card = "rounded-card border border-line bg-surface p-4";
const pill = "inline-block rounded-control px-2 py-0.5 text-sm font-medium";

// ---------------------------------------------------------------- confidence band
export function BandMeter({ band, confidence }: { band: ConfidenceBand; confidence: number | null | undefined }) {
  const { t, locale } = useI18n();
  const two = { minimumFractionDigits: 2, maximumFractionDigits: 2 };
  const low = formatNumber(locale, BAND_THRESHOLDS.low, two);
  const high = formatNumber(locale, BAND_THRESHOLDS.high, two);
  const marker = bandMarkerPercent(confidence);
  const score = confidence == null ? null : formatNumber(locale, confidence, two);
  const segments = [
    { id: "low", width: BAND_THRESHOLDS.low * 100, cls: "bg-band-low", text: t("band.low.range", { low }) },
    { id: "medium", width: (BAND_THRESHOLDS.high - BAND_THRESHOLDS.low) * 100, cls: "bg-band-medium", text: t("band.medium.range", { low, high }) },
    { id: "high", width: (1 - BAND_THRESHOLDS.high) * 100, cls: "bg-band-high", text: t("band.high.range", { high }) },
  ] as const;
  return (
    <div>
      <p className="eyebrow">{t("band.label")}</p>
      <p className="text-lg font-bold">{score ? t("result.confidence.value", { band: bandLabel(t, band), score }) : bandLabel(t, band)}</p>
      <div role="img" aria-label={`${bandAria(t, band)}${score ? ` (${score})` : ""}`} className="relative mt-2">
        <div className="flex h-3 overflow-hidden rounded-full bg-band-track">
          {segments.map((s) => (
            <div key={s.id} style={{ width: `${s.width}%` }} className={`${s.cls} ${s.id === band ? "" : "opacity-40"}`} />
          ))}
        </div>
        {marker != null && (
          <div aria-hidden="true" style={{ left: `${marker}%` }} className="absolute -top-1 h-5 w-1 -translate-x-1/2 rounded bg-ink" />
        )}
      </div>
      <ul className="mt-2 flex justify-between gap-2 text-xs text-ink-muted">
        {segments.map((s) => (
          <li key={s.id} className={s.id === band ? "font-bold text-ink" : ""}>{s.text}</li>
        ))}
      </ul>
      <p className="mt-2 text-sm">{bandExplanation(t, band)}</p>
    </div>
  );
}

// ---------------------------------------------------------------- sources
export function SourceList({ sources, advisoryRan }: { sources: AdvisorySource[]; advisoryRan: boolean }) {
  const { t, locale } = useI18n();
  if (sources.length === 0 && !advisoryRan) return null;
  return (
    <section className={card}>
      <h2 className="eyebrow">{t("result.sources.title")}</h2>
      {sources.length === 0 ? (
        <p className="mt-2">{t("source.noneVerified")}</p>
      ) : (
        <ul className="mt-2 space-y-4">
          {sources.map((s, i) => {
            const kind = sourceKind(s);
            const published = publishedDate(s);
            const url = safeSourceUrl(s.source_url);
            return (
              <li key={`${s.title}-${i}`} className="space-y-1">
                <p className="font-bold">{s.title}</p>
                <p className="text-sm text-ink-muted">{t("source.publisher", { name: s.publisher })}</p>
                <div className="flex flex-wrap gap-2">
                  {/* Verified is shown ONLY for an ingested, verified source. A demo source is always labelled as demo. */}
                  {kind === "verified" && <span className={`${pill} bg-success-bg text-success-fg`}>{t("source.verified")}</span>}
                  {kind === "demo" && <span className={`${pill} bg-warning-bg text-warning-fg`}>{t("source.demo")}</span>}
                  {kind === "unverified" && <span className={`${pill} bg-sunken text-ink-muted`}>{t("source.unverifiedNote")}</span>}
                  <span className={`${pill} ${s.stale ? "bg-danger-bg text-danger-fg" : "bg-sunken text-ink"}`}>
                    {s.stale ? t("source.stale") : t("source.upToDate")}
                  </span>
                  <span className={`${pill} bg-sunken text-ink`}>{s.structured ? t("source.structured") : t("source.generalText")}</span>
                </div>
                <p className="text-sm">{published ? t("source.published", { date: formatDate(locale, published) }) : t("source.dateMissing")}</p>
                {s.retrieved_at && <p className="text-sm text-ink-muted">{t("source.retrieved", { date: formatDateTime(locale, s.retrieved_at) })}</p>}
                {kind === "demo" && <p className="text-sm text-warning-fg">{t("source.demoNote")}</p>}
                {url && (
                  <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 items-center text-sm font-medium text-brand underline">
                    {t("source.open")}
                  </a>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

// ---------------------------------------------------------------- weather
export function WeatherCard({ weather, district }: { weather: WeatherResult; district?: string }) {
  const { t, locale } = useI18n();
  const n = (v: number | null | undefined, unit: "c" | "pct" | "mm" | "kmh", digits = 0) =>
    v == null ? null : t(`weather.unit.${unit}`, { n: formatNumber(locale, v, { maximumFractionDigits: digits }) });
  const rows: [string, string | null][] = [
    [t("weather.temperature"), n(weather.temperature_c, "c")],
    [t("weather.humidity"), n(weather.humidity_pct, "pct")],
    // an old reading is not used for crop advice, so it shows no forecast rows
    [t("weather.rain24"), weather.stale ? null : n(weather.rain_next_24h_mm, "mm", 1)],
    [t("weather.rainChance"), weather.stale ? null : n(weather.rain_probability_max_pct, "pct")],
    [t("weather.wind"), n(weather.wind_speed_kmh, "kmh", 1)],
  ];
  const when = formatDateTime(locale, weather.observed_at ?? weather.fetched_at);
  const provider = weather.provider ?? "";
  const provenance = !weather.available
    ? t("weather.provenance.unavailable")
    : weather.source === "live"
      ? t("weather.provenance.live", { provider, when })
      : weather.source === "cached"
        ? t(weather.stale ? "weather.provenance.cachedStale" : "weather.provenance.cached", { provider, when })
        : t("weather.provenance.demo");
  return (
    <section className={card}>
      <h2 className="eyebrow">{t("weather.title")}{district ? ` · ${district}` : ""}</h2>
      <p className="mt-1 text-sm">
        <span className={`${pill} ${weather.source === "live" ? "bg-success-bg text-success-fg" : "bg-warning-bg text-warning-fg"}`}>
          {weatherSourceLabel(t, weather.available ? (weather.stale ? "stale" : weather.source) : "unavailable")}
        </span>{" "}
        {provenance}
      </p>
      {weather.stale && <p className="mt-2 text-sm text-warning-fg">{t("weather.staleNote", { hours: WEATHER_STALE_HOURS })}</p>}
      {weather.available && (
        <dl className="mt-3 grid grid-cols-[1fr_auto] gap-x-4 gap-y-1">
          {rows.filter(([, v]) => v).map(([label, v]) => (
            <div key={label} className="contents">
              <dt className="text-ink-muted">{label}</dt>
              <dd className="text-end font-medium">{v}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}

// ---------------------------------------------------------------- what we observed
function useLeafPhoto(caseId: string, item: CaseOut | null) {
  const [url, setUrl] = useState<string | null>(null);
  const imageId = item?.images?.filter((i) => i.kind === "leaf_closeup").at(-1)?.id;
  useEffect(() => {
    if (!imageId) return;
    let current = true;
    getApiClient().imageSignedUrl(caseId, imageId).then(
      (r) => current && setUrl(r.url),
      () => undefined, // the photo is a nicety; a failed link just means no thumbnail
    );
    return () => {
      current = false;
    };
  }, [caseId, imageId]);
  return imageId ? url : null;
}

export function ObservedCard({ caseId, analysis, item }: { caseId: string; analysis: CaseAnalysisOut; item: CaseOut | null }) {
  const { t, locale } = useI18n();
  const photoUrl = useLeafPhoto(caseId, item);
  const rows = timelineRows(analysis.trace);
  const quality = rows.find((r) => r.step === "quality_gate");
  const vision = rows.find((r) => r.step === "vision");
  const ran = (r: typeof quality) => r && r.status === "completed";
  const two = { minimumFractionDigits: 2, maximumFractionDigits: 2 };

  const entries: [string, string][] = [];
  if (item?.district) entries.push([t("result.observed.district"), item.district]);
  if (item?.growth_stage) entries.push([t("result.observed.stage"), growthStageText(t, item.growth_stage)]);
  if (item?.symptom_started_at) entries.push([t("result.observed.started"), formatDate(locale, item.symptom_started_at)]);
  if (item?.recent_rainfall) entries.push([t("result.observed.rain"), item.recent_rainfall]);
  if (item?.description) entries.push([t("result.observed.more"), item.description]);

  return (
    <section className={card}>
      <h2 className="eyebrow">{t("result.observed.title")}</h2>
      <div className="mt-2 flex gap-3">
        {photoUrl && (
          // eslint-disable-next-line @next/next/no-img-element -- a short-lived signed URL from the API, not an optimisable asset
          <img src={photoUrl} alt={t("result.observed.photoAlt")} className="h-20 w-20 shrink-0 rounded-control object-cover" />
        )}
        <dl className="grid min-w-0 flex-1 grid-cols-[auto_1fr] gap-x-3 gap-y-1">
          <dt className="text-ink-muted">{t("result.observed.photoCheck")}</dt>
          <dd className="font-medium">
            {ran(quality) && quality?.detail.score != null
              ? t(quality.detail.passed === false ? "result.observed.photoFailed" : "result.observed.photoPassed", { score: formatNumber(locale, Math.round(quality.detail.score)) })
              : t("result.observed.notRun")}
          </dd>
          <dt className="text-ink-muted">{t("result.observed.leafReading")}</dt>
          <dd className="font-medium">
            {ran(vision) && vision?.detail.band
              ? `${t("result.observed.leafBand", { band: bandLabel(t, vision.detail.band) })}${vision.detail.confidence != null ? ` · ${formatNumber(locale, vision.detail.confidence, two)}` : ""}`
              : t("result.observed.notRun")}
          </dd>
        </dl>
      </div>
      {quality?.detail.passed === false && <QualityIssues analysis={analysis} />}
      {entries.length > 0 && (
        <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 border-t border-line pt-3">
          {entries.map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-ink-muted">{k}</dt>
              <dd dir="auto">{v}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}

function QualityIssues({ analysis }: { analysis: CaseAnalysisOut }) {
  const { t } = useI18n();
  const raw = stepOf(analysis.trace, "quality_gate")?.detail?.issues;
  const issues = Array.isArray(raw) ? raw.filter((x): x is string => typeof x === "string") : [];
  const known = issues.filter(isQualityIssue);
  if (known.length === 0) return null;
  return (
    <ul className="mt-2 list-disc ps-5 text-sm">
      {known.map((i) => (
        <li key={i}>{qualityIssueText(t, i)}</li>
      ))}
    </ul>
  );
}

// ---------------------------------------------------------------- the condition
export function ConditionCard({ analysis }: { analysis: CaseAnalysisOut }) {
  const { t } = useI18n();
  const label = analysis.result.preliminary_label;
  if (!label) return null;
  return (
    <section className={card}>
      <h2 className="eyebrow">{t("result.condition.title")}</h2>
      <p className="mt-1 text-title font-bold">{categoryLabel(t, label)}</p>
      <p className="mt-1">{t("safety.preliminary")}</p>
      {analysis.confidence_band && (
        <div className="mt-3 border-t border-line pt-3">
          <BandMeter band={analysis.confidence_band} confidence={analysis.result.confidence} />
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------- missing information
const isMissing = (v: string): v is MissingInformationCode => (MISSING_INFORMATION_CODES as readonly string[]).includes(v);

export function MissingList({ codes }: { codes: string[] }) {
  const { t } = useI18n();
  const known = codes.filter(isMissing);
  if (known.length === 0) return null;
  return (
    <section className={card}>
      <h2 className="eyebrow">{t("result.missing.title")}</h2>
      <ol className="mt-2 space-y-2">
        {known.map((code, i) => (
          <li key={code} className="flex gap-3">
            <span aria-hidden="true" className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-sm font-bold ${i === 0 ? "bg-warning-fg text-white" : "bg-sunken text-ink"}`}>
              {i + 1}
            </span>
            <div>
              <p className="font-medium">{missingCopy(t, code).title}</p>
              <p className="text-sm text-ink-muted">{missingCopy(t, code).hint}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
