"use client";

import { useCallback, useEffect, useState } from "react";
import { apiErrorText, categoryLabel, growthStageText, intentLabel, reasonCopy, traceStepLabel } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { formatDate, formatDateTime, formatNumber } from "@/i18n/format";
import { ApiError, getApiClient, type ApiErrorCode } from "@/lib/api-client";
import type { Category, ExpertCaseDetail, ExpertReviewRecord, ImageOut, TraceStepId } from "@/lib/api-types";
import { CATEGORIES, TRACE_STEP_IDS } from "@/lib/api-types";
import { canReview, outputPairs } from "@/lib/expert";
import { safeSourceUrl } from "@/lib/checks/result";
import { SourceList } from "@/components/result/parts";
import { ReviewForm } from "./ReviewForm";

const box = "rounded-card border border-line bg-surface p-4";
type Load = { status: "loading" } | { status: "error"; code: ApiErrorCode } | { status: "ready"; detail: ExpertCaseDetail };
const isCategory = (v: string | null | undefined): v is Category => !!v && (CATEGORIES as readonly string[]).includes(v);
const isStep = (v: string): v is TraceStepId => (TRACE_STEP_IDS as readonly string[]).includes(v);

function Photo({ caseId, image }: { caseId: string; image: ImageOut }) {
  const { t } = useI18n();
  const [state, setState] = useState<{ url: string } | "failed" | null>(null);
  useEffect(() => {
    let current = true;
    getApiClient().imageSignedUrl(caseId, image.id).then(
      (r) => current && setState({ url: r.url }),
      () => current && setState("failed"),
    );
    return () => {
      current = false;
    };
  }, [caseId, image.id]);
  const kind = t(`image.kind.${image.kind}`);
  if (state === "failed") return <p className="text-sm text-danger-fg">{t("ex.photos.failed")}</p>;
  if (!state) return <div className="h-40 animate-pulse rounded-control bg-skeleton" aria-hidden="true" />;
  return (
    <figure>
      {/* eslint-disable-next-line @next/next/no-img-element -- a short-lived signed URL from the API */}
      <img src={state.url} alt={t("ex.photos.alt", { kind })} className="max-h-64 w-full rounded-control object-contain bg-sunken" />
      <figcaption className="text-sm text-ink-muted">{kind}</figcaption>
    </figure>
  );
}

function ReviewResult({ record }: { record: ExpertReviewRecord }) {
  const { t, locale } = useI18n();
  const url = safeSourceUrl(record.recommended_advisory?.url);
  return (
    <section className={`${box} space-y-2`}>
      <h3 className="text-lg font-bold">{t("ex.result.title")}</h3>
      {record.decision && <p className="font-medium">{t(`expert.decision.${record.decision}`)}</p>}
      {record.label && <p>{t("ex.result.category")}: {isCategory(record.label) ? categoryLabel(t, record.label) : record.label}</p>}
      {record.notes && (
        <div>
          <p className="eyebrow">{t("expert.notes.label")}</p>
          <p dir="auto" className="whitespace-pre-wrap">{record.notes}</p>
        </div>
      )}
      {record.recommended_advisory && (
        <p>
          {t("ex.result.advisory")}: {record.recommended_advisory.title} · {record.recommended_advisory.publisher}
          {url && <> · <a href={url} target="_blank" rel="noopener noreferrer" className="text-brand underline">{url}</a></>}
        </p>
      )}
      {record.reviewed_at && <p className="text-sm text-ink-muted">{t("expert.reviewedAt", { when: formatDateTime(locale, record.reviewed_at) })}</p>}
      {record.status === "awaiting_farmer" && <p className="text-sm">{t("ex.result.awaiting")}</p>}
      {record.status === "follow_up_received" && <p className="text-sm">{t("ex.result.followUp")}</p>}
    </section>
  );
}

export function CaseDetail({ caseId, onReviewed }: { caseId: string; onReviewed: () => void }) {
  const { t, locale } = useI18n();
  const [load, setLoad] = useState<Load>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    let current = true;
    getApiClient().getExpertCase(caseId).then(
      (detail) => current && setLoad({ status: "ready", detail }),
      (e: unknown) => current && setLoad({ status: "error", code: e instanceof ApiError ? e.code : "unknown" }),
    );
    return () => {
      current = false;
    };
  }, [caseId, attempt]);

  const reload = useCallback(() => {
    setLoad({ status: "loading" });
    setAttempt((n) => n + 1);
  }, []);

  if (load.status === "loading") {
    return (
      <div aria-busy="true" className="space-y-3">
        <p role="status" className="text-ink-muted">{t("ex.loading")}</p>
        {[24, 40, 32].map((h, i) => <div key={i} style={{ height: h * 4 }} className="animate-pulse rounded-card bg-skeleton" aria-hidden="true" />)}
      </div>
    );
  }
  if (load.status === "error") {
    return (
      <div role="alert" className="space-y-2 rounded-card border border-danger-solid bg-danger-card p-4">
        <p className="font-bold text-danger-fg">{t("ex.error.title")}</p>
        <p>{apiErrorText(t, load.code)}</p>
        <button type="button" onClick={reload} className="min-h-11 rounded-control bg-brand px-4 font-bold text-white">{t("common.tryAgain")}</button>
      </div>
    );
  }

  const { detail } = load;
  const cur = detail.current;
  const snap = cur.snapshot;
  const reason = detail.escalation_reason_code ? reasonCopy(t, detail.escalation_reason_code, detail.escalation_reason_detail, { district: snap.district }) : null;
  const code = [detail.escalation_reason_code, detail.escalation_reason_detail].filter(Boolean).join(":");
  const meta: [string, string][] = [
    [t("ex.meta.district"), snap.district],
    [t("ex.meta.stage"), snap.growth_stage ? growthStageText(t, snap.growth_stage) : ""],
    [t("ex.meta.started"), snap.symptom_started_at ? formatDate(locale, snap.symptom_started_at) : ""],
    [t("ex.meta.rain"), snap.recent_rainfall ?? ""],
    [t("ex.meta.intent"), snap.intent ? intentLabel(t, snap.intent) : ""],
    [t("ex.meta.path"), snap.path ?? ""],
    [t("ex.meta.more"), snap.description ?? ""],
  ];
  const images = snap.images ?? [];
  const predictions = snap.predictions ?? [];

  return (
    <article className="space-y-4">
      <header>
        <p className="eyebrow">{t("ex.case.eyebrow", { id: detail.case_id.slice(0, 8), when: formatDateTime(locale, cur.created_at) })}</p>
        <span className="mt-1 inline-block rounded-control bg-info-bg px-2 py-0.5 text-sm font-medium text-info-fg">{t(`expert.status.${cur.status}`)}</span>
        <h2 dir="auto" className="mt-2 text-title font-bold">{snap.question}</h2>
        <p className="font-mono text-sm text-ink-muted">{code ? `${code} · ` : ""}run {cur.routing_run_id.slice(0, 8)}</p>
        {reason && <p className="mt-1 text-sm text-ink-muted">{reason.body}</p>}
      </header>

      <dl className={`${box} grid gap-x-6 gap-y-2 sm:grid-cols-2`}>
        {meta.map(([k, v]) => (
          <div key={k}>
            <dt className="text-sm text-ink-muted">{k}</dt>
            <dd dir="auto" className="break-words">{v || <span className="text-ink-muted">{t("ex.notGiven")}</span>}</dd>
          </div>
        ))}
      </dl>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className={box}>
          <h3 className="eyebrow">{t("ex.missing.title")}</h3>
          {(snap.missing_information ?? []).length === 0 ? (
            <p className="mt-2">{t("ex.missing.none")}</p>
          ) : (
            <ul className="mt-2 list-disc ps-5">
              {(snap.missing_information ?? []).map((m) => <li key={m}>{m}</li>)}
            </ul>
          )}
          <p className="mt-2 text-xs text-ink-muted">{t("ex.missing.note")}</p>
        </section>

        <div className="space-y-4">
          <section className={box}>
            <h3 className="eyebrow">{t("ex.photos.title")}</h3>
            {images.length === 0 ? <p className="mt-2">{t("ex.photos.none")}</p> : <div className="mt-2 space-y-3">{images.map((im) => <Photo key={im.id} caseId={detail.case_id} image={im} />)}</div>}
          </section>
          <SourceList sources={snap.sources ?? []} advisoryRan />
          <section className={box}>
            <h3 className="eyebrow">{t("ex.followups.title")}</h3>
            {(snap.follow_ups ?? []).length === 0 ? <p className="mt-2">{t("ex.followups.none")}</p> : (
              <ul className="mt-2 list-disc ps-5">{(snap.follow_ups ?? []).map((f, i) => <li key={i} dir="auto">{f}</li>)}</ul>
            )}
          </section>
        </div>
      </div>

      <section className={`${box} overflow-x-auto`}>
        <h3 className="eyebrow">{t("ex.predictions.title")}</h3>
        {predictions.length === 0 ? <p className="mt-2">{t("ex.predictions.none")}</p> : (
          <table className="mt-2 w-full min-w-[32rem] text-start text-sm">
            <thead>
              <tr className="text-ink-muted">
                {(["step", "model", "label", "confidence", "output"] as const).map((c) => <th key={c} scope="col" className="py-1 pe-3 text-start font-medium">{t(`ex.col.${c}`)}</th>)}
              </tr>
            </thead>
            <tbody>
              {predictions.map((p, i) => (
                <tr key={`${p.step}-${i}`} className="border-t border-line align-top">
                  <td className="py-1 pe-3">{isStep(p.step) ? traceStepLabel(t, p.step) : p.step}</td>
                  <td className="py-1 pe-3 font-mono text-xs">{p.model_name}</td>
                  <td className="py-1 pe-3">{p.label ? (isCategory(p.label) ? categoryLabel(t, p.label) : p.label) : "—"}</td>
                  <td className="py-1 pe-3">{p.confidence == null ? "—" : formatNumber(locale, p.confidence, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  <td className="py-1 font-mono text-xs">{outputPairs(p.output).map(([k, v]) => `${k}: ${v}`).join(" · ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="mt-2 text-sm text-ink-muted">
          {detail.history.length <= 1 ? t("ex.history.one") : t("ex.history.many", { n: detail.history.length })}
        </p>
      </section>

      {sent && <p role="status" className="rounded-card bg-success-bg p-3 font-medium text-success-fg">{t("ex.review.success")}</p>}
      {canReview(cur.status) && !sent ? (
        <ReviewForm
          caseId={detail.case_id}
          onSent={() => {
            setSent(true);
            onReviewed();
            reload();
          }}
        />
      ) : (
        cur.decision || cur.status !== "pending_review" ? <ReviewResult record={cur} /> : null
      )}
    </article>
  );
}
