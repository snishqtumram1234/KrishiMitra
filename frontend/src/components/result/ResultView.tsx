"use client";

import Link from "next/link";
import { apiErrorText, categoryLabel, reasonCopy, stateCopy } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { formatDateTime } from "@/i18n/format";
import type { CaseAnalysisOut, CaseOut, DecisionState } from "@/lib/api-types";
import { checkIsSafe, showsCondition, stepOf, weatherOf } from "@/lib/checks/result";
import { ExpertRequest, NextStep } from "./actions";
import { BandMeter, ConditionCard, MissingList, ObservedCard, SourceList, WeatherCard } from "./parts";
import { RouteDetails } from "./RouteDetails";
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
      <p className="mt-1">{unavailable ? t("safety.unavailable") : t("safety.note")}</p>
    </aside>
  );
}

function Skeleton() {
  const { t } = useI18n();
  return (
    <div aria-busy="true" className="space-y-3">
      <p role="status" className="text-ink-muted">{t("result.loading")}</p>
      {[28, 40, 40, 24].map((h, i) => (
        <div key={i} style={{ height: h * 4 }} className="animate-pulse rounded-card bg-skeleton" aria-hidden="true" />
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
        <div role="alert" className="space-y-2 rounded-card border border-danger-solid bg-danger-card p-4">
          <h2 className="text-lg font-bold text-danger-fg">{t("result.error.title")}</h2>
          <p>{apiErrorText(t, state.code)}</p>
          {checkIsSafe(state.code) && <p className="text-sm">{t("result.error.saved")}</p>}
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={reload} className="min-h-11 rounded-control bg-brand px-4 font-bold text-white">{t("common.tryAgain")}</button>
            <Link href="/dashboard" className="inline-flex min-h-11 items-center px-3 font-medium text-brand underline">{t("result.toDashboard")}</Link>
          </div>
        </div>
        <SafetyNote unavailable />
      </div>
    );
  }

  if (state.status === "notAnalyzed") {
    return (
      <div className="space-y-4">
        <p className="inline-block rounded-control bg-sunken px-2 py-1 text-sm font-medium">{t("result.notAnalyzed.title")}</p>
        <div className="space-y-3 rounded-card border border-dashed border-control-border bg-field p-4">
          <h2 className="text-lg font-bold">{t("result.notAnalyzed.title")}</h2>
          <p className="text-ink-muted">{t("result.notAnalyzed.body")}</p>
          <Link href={`/checks/${caseId}/progress`} className="inline-flex min-h-12 items-center rounded-control bg-brand px-4 font-bold text-white">{t("progress.run")}</Link>
        </div>
        <SafetyNote unavailable />
      </div>
    );
  }

  return <ResultReady caseId={caseId} analysis={state.analysis} item={state.item} />;
}

export function ResultReady({ caseId, analysis, item }: { caseId: string; analysis: CaseAnalysisOut; item: CaseOut | null }) {
  const { t, locale } = useI18n();
  const s = analysis.state;
  const copy = stateCopy(t, s);
  const reason = analysis.reason_code ? reasonCopy(t, analysis.reason_code, analysis.reason_detail, { district: item?.district }) : null;
  const weather = weatherOf(analysis);
  const advisoryRan = stepOf(analysis.trace, "advisory")?.status !== undefined && stepOf(analysis.trace, "advisory")?.status !== "skipped";
  const sources = analysis.result.sources ?? [];
  const condition = showsCondition(analysis);
  const expert = analysis.expert;

  return (
    <article className="space-y-5">
      <div>
        <p className="inline-block rounded-control bg-info-bg px-2 py-1 text-sm font-medium text-info-fg">{copy.badge}</p>
        <p className="mt-1 text-sm text-ink-muted">{t("result.saved", { when: formatDateTime(locale, analysis.created_at) })}</p>
        {item && (
          <p className="mt-2">
            <span className="eyebrow block">{t("result.question")}</span>
            <span dir="auto">{item.symptom_context}</span>
          </p>
        )}
      </div>

      <section className={`rounded-card border p-4 ${TONE[s]}`}>
        <h2 className="text-title font-bold">{copy.label}</h2>
        <p className="mt-1">{copy.summary}</p>
        {reason && (
          <div className="mt-3 border-t border-current/20 pt-3">
            <p className="font-bold">{reason.title}</p>
            <p className="mt-1">{reason.body}</p>
          </div>
        )}
      </section>

      {expert && (
        <section className="space-y-2 rounded-card border border-info-fg bg-info-bg p-4 text-info-fg">
          <h2 className="font-bold">{t("expert.card.title")}</h2>
          <p>{t("expert.card.body")}</p>
          <p className="text-sm">{t("expert.status.label")}: {t(`expert.status.${expert.status}`)}</p>
          {expert.decision === "likely" && expert.label && <p>{t("expert.likely", { label: categoryLabel(t, expert.label) })}</p>}
          {expert.notes && (
            <div>
              <p className="eyebrow">{t("expert.notes.label")}</p>
              <p dir="auto" className="whitespace-pre-wrap text-ink">{expert.notes}</p>
            </div>
          )}
          {expert.reviewed_at && <p className="text-sm">{t("expert.reviewedAt", { when: formatDateTime(locale, expert.reviewed_at) })}</p>}
        </section>
      )}

      {condition ? <ConditionCard analysis={analysis} /> : s === "PRELIMINARY_GUIDANCE" && analysis.confidence_band ? (
        <section className="rounded-card border border-line bg-surface p-4"><BandMeter band={analysis.confidence_band} confidence={analysis.result.confidence} /></section>
      ) : null}

      {weather && <WeatherCard weather={weather} district={item?.district} />}

      {analysis.result.path === "image_diagnosis" && <ObservedCard caseId={caseId} analysis={analysis} item={item} />}

      <MissingList codes={analysis.missing_information} />
      <SourceList sources={sources} advisoryRan={advisoryRan} />

      <NextStep caseId={caseId} analysis={analysis} />
      <ExpertRequest caseId={caseId} analysis={analysis} />

      <SafetyNote />
      <RouteDetails analysis={analysis} />

      <nav className="flex flex-wrap gap-x-4">
        <Link href={`/checks/${caseId}/progress`} className="inline-flex min-h-11 items-center font-medium text-brand underline">{t("progress.title")}</Link>
        <Link href="/checks/new" className="inline-flex min-h-11 items-center font-medium text-brand underline">{t("result.another")}</Link>
        <Link href="/dashboard" className="inline-flex min-h-11 items-center font-medium text-brand underline">{t("result.toDashboard")}</Link>
      </nav>
    </article>
  );
}
