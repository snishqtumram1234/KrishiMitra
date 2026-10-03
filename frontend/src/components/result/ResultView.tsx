"use client";

import Link from "next/link";
import { useState } from "react";
import {
  apiErrorText,
  bandLabel,
  categoryLabel,
  reasonCopy,
  stateCopy,
} from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { localExcerpt } from "@/i18n/excerpts";
import { formatNumber } from "@/i18n/format";
import type { CaseAnalysisOut, CaseOut, DecisionState } from "@/lib/api-types";
import {
  checkIsSafe,
  showsCondition,
  stepOf,
  weatherOf,
} from "@/lib/checks/result";
import { ExpertRequest, NextStep } from "./actions";
import {
  ConditionCard,
  MissingList,
  ObservedCard,
  SourceList,
  useLeafPhoto,
  WeatherCard,
} from "./parts";
import { RouteDetails } from "./RouteDetails";
import { ActionBar, HelpCard, ReportHeader, WeatherRisk } from "./addons";
import { SPREAD_CONDITIONS, summaryText } from "@/lib/checks/risk";
import { useCheck } from "./useCheck";

const TONE: Record<DecisionState, string> = {
  NEEDS_BETTER_IMAGE: "border-warning-accent bg-warning-bg text-warning-fg",
  NEEDS_MORE_CONTEXT: "border-warning-accent bg-warning-bg text-warning-fg",
  PRELIMINARY_GUIDANCE: "border-line bg-surface text-ink",
  EXPERT_REVIEW: "border-info-fg bg-info-bg text-info-fg",
  UNSUPPORTED: "border-line bg-sunken text-ink",
};

function SafetyNote({ unavailable = false }: { unavailable?: boolean }) {
  const { t } = useI18n();
  return (
    <aside className="on-dark rounded-card bg-soil-900 p-4 text-white">
      <h2 className="font-bold">{t("safety.noteTitle")}</h2>
      <p className="mt-1">
        {unavailable ? t("safety.unavailable") : t("safety.note")}
      </p>
    </aside>
  );
}

function Skeleton() {
  const { t } = useI18n();
  return (
    <div aria-busy="true" className="space-y-3">
      <p role="status" className="text-ink-muted">
        {t("result.loading")}
      </p>
      {[28, 40, 40, 24].map((h, i) => (
        <div
          key={i}
          style={{ height: h * 4 }}
          className="animate-pulse rounded-card bg-skeleton"
          aria-hidden="true"
        />
      ))}
    </div>
  );
}

/**
 * The Result screen. It renders only from structured fields: state, reason_code/detail, confidence_band,
 * missing_information, follow_up_options, sources and the recorded trace. The backend's English `message` is never shown.
 */
export function ResultView({ caseId }: { caseId: string }) {
  const { t } = useI18n();
  const { state, reload } = useCheck(caseId);

  if (state.status === "loading") return <Skeleton />;

  if (state.status === "error") {
    return (
      <div className="space-y-4">
        <div
          role="alert"
          className="space-y-2 rounded-card border border-danger-solid bg-danger-card p-4"
        >
          <h2 className="text-lg font-bold text-danger-fg">
            {t("result.error.title")}
          </h2>
          <p>{apiErrorText(t, state.code)}</p>
          {checkIsSafe(state.code) && (
            <p className="text-sm">{t("result.error.saved")}</p>
          )}
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={reload}
              className="min-h-11 rounded-control bg-brand px-4 font-bold text-white"
            >
              {t("common.tryAgain")}
            </button>
            <Link
              href="/dashboard"
              className="inline-flex min-h-11 items-center px-3 font-medium text-brand underline"
            >
              {t("result.toDashboard")}
            </Link>
          </div>
        </div>
        <SafetyNote unavailable />
      </div>
    );
  }

  if (state.status === "notAnalyzed") {
    return (
      <div className="space-y-4">
        <p className="inline-block rounded-control bg-sunken px-2 py-1 text-sm font-medium">
          {t("result.notAnalyzed.title")}
        </p>
        <div className="space-y-3 rounded-card border border-dashed border-control-border bg-field p-4">
          <h2 className="text-lg font-bold">{t("result.notAnalyzed.title")}</h2>
          <p className="text-ink-muted">{t("result.notAnalyzed.body")}</p>
          <Link
            href={`/checks/${caseId}/progress`}
            className="inline-flex min-h-12 items-center rounded-control bg-brand px-4 font-bold text-white"
          >
            {t("progress.run")}
          </Link>
        </div>
        <SafetyNote unavailable />
      </div>
    );
  }

  return (
    <ResultReady caseId={caseId} analysis={state.analysis} item={state.item} />
  );
}

/** Marks a translated source passage as a translation and keeps the exact English original one click away. */
function TranslationNote({ original }: { original: string }) {
  const { t } = useI18n();
  return (
    <details className="text-sm text-ink-muted">
      <summary className="cursor-pointer">{t("result.translated.note")}</summary>
      <p lang="en" className="mt-2 leading-relaxed">
        {original}
      </p>
    </details>
  );
}

/** "1.Use recommended seed rate. ... 2.Avoid ..." -> one item per numbered practice, text unchanged. */
export function splitPractices(text: string): string[] {
  return text
    .split(/(?:^|\s)\d+\.(?=\S)/)
    .map((x) => x.trim())
    .filter(Boolean);
}

export function ResultReady({
  caseId,
  analysis,
  item,
}: {
  caseId: string;
  analysis: CaseAnalysisOut;
  item: CaseOut | null;
}) {
  const { t, locale } = useI18n();
  const [more, setMore] = useState(false);
  const s = analysis.state;
  const copy = stateCopy(t, s);
  const reason = analysis.reason_code
    ? reasonCopy(t, analysis.reason_code, analysis.reason_detail, { district: item?.district })
    : null;
  const weather = weatherOf(analysis);
  const advisoryRan =
    stepOf(analysis.trace, "advisory")?.status !== undefined && stepOf(analysis.trace, "advisory")?.status !== "skipped";
  const sources = analysis.result.sources ?? [];
  const expert = analysis.expert;
  const photoUrl = useLeafPhoto(caseId, item);

  // What is happening: the condition (only in a preliminary-guidance answer), the verified description, or the reason.
  const label = showsCondition(analysis) ? analysis.result.preliminary_label : null;
  const band = analysis.confidence_band;
  const pct = label && analysis.result.confidence != null ? Math.round(analysis.result.confidence * 100) : null;
  const description = sources.find((x) => x.excerpt && x.excerpt_kind !== "management");
  const practiceSources = sources.filter((x) => x.excerpt && x.excerpt_kind === "management");
  const practiceText = practiceSources.map((x) => localExcerpt(x.excerpt ?? "", locale));
  const practices = practiceText.flatMap((x) => splitPractices(x.text));
  const practicesLang = practiceText.every((x) => x.translated) ? "mr" : "en";
  const cause = description?.excerpt ? localExcerpt(description.excerpt, locale) : null;
  const heading = label ? categoryLabel(t, label) : copy.label;
  const fromPhoto = analysis.result.path === "image_diagnosis";
  const actionHere = s === "NEEDS_BETTER_IMAGE" || s === "NEEDS_MORE_CONTEXT" || expert?.status === "awaiting_farmer";
  const cite = (x: (typeof sources)[number]) =>
    t("result.citation", { publisher: x.publisher, page: x.page != null ? formatNumber(locale, x.page) : "-" });
  const tone = band === "high" ? "text-band-high" : band === "medium" ? "text-band-medium" : "text-band-low";
  const spread = label ? SPREAD_CONDITIONS[label] : undefined;
  const spoken = summaryText([
    `${t("result.happening.title")}: ${heading}`,
    pct != null ? t("result.match", { pct: formatNumber(locale, pct) }) : null,
    label === "healthy" ? t("result.healthy.body") : (cause?.text ?? reason?.body ?? copy.summary),
    practices.length ? `${t("result.todo.title")}: ${practices.map((x, i) => `${i + 1}. ${x}`).join(" ")}` : null,
    t("safety.note"),
    fromPhoto ? t("result.preliminaryNote") : null,
  ]);

  return (
    <article className="mx-auto max-w-4xl space-y-6">
      <ReportHeader caseId={caseId} createdAt={analysis.created_at} item={item} />
      <ActionBar text={spoken} />

      {/* ---------------------------------------------------------------- 1. What is happening */}
      <section className="overflow-hidden rounded-card border border-brand bg-surface">
        <div className="bg-brand-wash p-5 sm:p-7">
          <p className="eyebrow">{t("result.happening.title")}</p>
          <div className="mt-3 flex flex-wrap items-start justify-between gap-5">
            <div className="min-w-0 flex-1">
              <h2 className="text-hero font-bold leading-tight">{heading}</h2>
              {pct != null && band && (
                <p className="mt-2 inline-flex items-center gap-2 rounded-control bg-surface px-3 py-1 text-sm font-medium">
                  <span className={tone}>{t("result.match", { pct: formatNumber(locale, pct) })}</span>
                  <span className="text-ink-muted">· {t("result.confidence.caption", { band: bandLabel(t, band) })}</span>
                </p>
              )}
            </div>
            {photoUrl && fromPhoto && (
              // eslint-disable-next-line @next/next/no-img-element -- a short-lived signed URL from the API
              <img src={photoUrl} alt={t("result.observed.photoAlt")} className="h-28 w-28 shrink-0 rounded-card object-cover sm:h-32 sm:w-32" />
            )}
          </div>
        </div>
        <div className="space-y-3 p-5 sm:p-7">
          {/* a photo check leads with the cause; weather leads only when the question was about weather */}
          {weather && !fromPhoto ? (
            <WeatherCard weather={weather} district={item?.district} />
          ) : label === "healthy" ? (
            <p className="text-lg leading-relaxed">{t("result.healthy.body")}</p>
          ) : description ? (
            <>
              <blockquote lang={cause?.lang} className="text-lg leading-relaxed">
                {cause?.text}
              </blockquote>
              <p className="text-sm text-ink-muted">
                {description.title} · {cite(description)}
              </p>
              {cause?.translated && <TranslationNote original={description.excerpt ?? ""} />}
            </>
          ) : (
            <p className="text-lg leading-relaxed">{reason?.body ?? copy.summary}</p>
          )}
          {fromPhoto && <p className="text-sm text-ink-muted">{t("result.preliminaryNote")}</p>}
        </div>
      </section>

      {spread && item?.district && description && (
        <WeatherRisk district={item.district} conditions={spread} sourceTitle={description.title} />
      )}

      {/* ---------------------------------------------------------------- 2. What you can do */}
      <section className="rounded-card border border-line bg-surface p-5 sm:p-7">
        <p className="eyebrow">{t("result.todo.title")}</p>
        {practices.length > 0 ? (
          <>
            <ol className="mt-4 space-y-3">
              {practices.map((item, i) => (
                <li key={i} className="flex gap-3">
                  <span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand text-sm font-bold text-white">
                    {i + 1}
                  </span>
                  <span lang={practicesLang} className="pt-0.5 text-lg leading-relaxed">
                    {item}
                  </span>
                </li>
              ))}
            </ol>
            <p className="mt-3 text-sm text-ink-muted">
              {practiceSources[0].title} · {cite(practiceSources[0])}
            </p>
            {practicesLang === "mr" && (
              <TranslationNote original={practiceSources.map((x) => x.excerpt ?? "").join(" ")} />
            )}
          </>
        ) : !actionHere && !expert ? (
          <p className="mt-3 text-lg">{t("result.todo.none")}</p>
        ) : null}

        {actionHere && (
          <div className="mt-4">
            <NextStep caseId={caseId} analysis={analysis} />
          </div>
        )}

        {expert && (
          <div className="mt-4 space-y-1 rounded-card bg-info-bg p-4 text-info-fg">
            <p className="font-bold">{t("expert.card.title")}</p>
            <p>{t("expert.card.body")}</p>
            <p className="text-sm">
              {t("expert.status.label")}: {t(`expert.status.${expert.status}`)}
            </p>
            {expert.decision === "likely" && expert.label && <p>{t("expert.likely", { label: categoryLabel(t, expert.label) })}</p>}
            {expert.notes && (
              <p dir="auto" className="whitespace-pre-wrap text-ink">
                {expert.notes}
              </p>
            )}
          </div>
        )}

        <p className="on-dark mt-5 rounded-card bg-soil-900 p-4 text-white">{t("safety.note")}</p>
        <div className="mt-4">
          <ExpertRequest caseId={caseId} analysis={analysis} />
        </div>
      </section>

      <HelpCard />

      {/* ---------------------------------------------------------------- everything else, folded away */}
      <section className="print:hidden">
        <button
          type="button"
          aria-expanded={more}
          onClick={() => setMore((m) => !m)}
          className="inline-flex min-h-11 items-center gap-2 font-medium text-brand underline"
        >
          {more ? t("result.more.hide") : t("result.more.show")}
        </button>
        {more && (
          <div className="mt-4 grid gap-5 lg:grid-cols-2 lg:items-start">
            <div className="space-y-5">
              <section className={`rounded-card border p-4 ${TONE[s]}`}>
                <h3 className="font-bold">{copy.label}</h3>
                <p className="mt-1">{copy.summary}</p>
                {reason && (
                  <p className="mt-2 text-sm">
                    {reason.title}: {reason.body}
                  </p>
                )}
              </section>
              {label && <ConditionCard analysis={analysis} />}
              {!actionHere && <NextStep caseId={caseId} analysis={analysis} />}
              {fromPhoto && <ObservedCard caseId={caseId} analysis={analysis} item={item} />}
              {fromPhoto && weather && <WeatherCard weather={weather} district={item?.district} />}
            </div>
            <div className="space-y-5">
              <MissingList codes={analysis.missing_information} />
              <SourceList sources={sources} advisoryRan={advisoryRan} />
              <RouteDetails analysis={analysis} />
              <nav className="flex flex-wrap gap-x-4">
                <Link href={`/checks/${caseId}/progress`} className="inline-flex min-h-11 items-center font-medium text-brand underline">
                  {t("progress.title")}
                </Link>
                <Link href="/checks/new" className="inline-flex min-h-11 items-center font-medium text-brand underline">
                  {t("result.another")}
                </Link>
                <Link href="/dashboard" className="inline-flex min-h-11 items-center font-medium text-brand underline">
                  {t("result.toDashboard")}
                </Link>
              </nav>
            </div>
          </div>
        )}
      </section>
    </article>
  );
}
