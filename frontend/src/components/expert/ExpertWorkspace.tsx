"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { apiErrorText } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { formatDateTime } from "@/i18n/format";
import { ApiError, getApiClient, type ApiErrorCode } from "@/lib/api-client";
import type { ExpertCaseSummary } from "@/lib/api-types";
import { countByStatus, STATUS_FILTERS, tagKey, type StatusFilter } from "@/lib/expert";
import { CaseDetail } from "./CaseDetail";

type Rows = { status: "loading" } | { status: "error"; code: ApiErrorCode } | { status: "ready"; rows: ExpertCaseSummary[] };

const href = (status: StatusFilter, caseId: string | null) => `/expert?status=${status}${caseId ? `&case=${caseId}` : ""}`;

/** Queue on the left, the open case on the right. The filter and the open case live in the URL, so a link or a refresh keeps them. */
export function ExpertWorkspace({ status, caseId }: { status: StatusFilter; caseId: string | null }) {
  const { t, locale } = useI18n();
  const [data, setData] = useState<Rows>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  // One call for everything: the chips' counts and every filtered view are derived from it.
  useEffect(() => {
    let current = true;
    getApiClient().listExpertCases("all").then(
      (rows) => current && setData({ status: "ready", rows }),
      (e: unknown) => current && setData({ status: "error", code: e instanceof ApiError ? e.code : "unknown" }),
    );
    return () => {
      current = false;
    };
  }, [attempt]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  const retry = () => {
    setData({ status: "loading" });
    setAttempt((n) => n + 1);
  };

  const rows = data.status === "ready" ? data.rows : [];
  const counts = countByStatus(rows);
  const shown = rows.filter((r) => status === "all" || r.status === status);

  return (
    <div className="space-y-4">
      <h1 className="text-title font-bold">{t("ex.queue.title")}</h1>
      <div className="grid gap-6 lg:grid-cols-[22rem_1fr]">
        <section aria-label={t("ex.queue.title")} className="space-y-3">
          <nav aria-label={t("ex.filter.label")} className="flex flex-wrap gap-2">
            {STATUS_FILTERS.map((s) => (
              <Link
                key={s}
                href={href(s, caseId)}
                aria-current={s === status ? "page" : undefined}
                className={`inline-flex min-h-11 items-center rounded-control border px-3 text-sm font-medium ${s === status ? "border-brand bg-brand text-white" : "border-control-border bg-surface"}`}
              >
                {s === "all" ? t("ex.filter.all") : t(`expert.status.${s}`)}
                {data.status === "ready" && ` · ${counts[s]}`}
              </Link>
            ))}
          </nav>

          {data.status === "loading" && (
            <div aria-busy="true" className="space-y-2">
              <p role="status" className="text-ink-muted">{t("ex.loading")}</p>
              {[0, 1, 2].map((i) => <div key={i} className="h-20 animate-pulse rounded-card bg-skeleton" aria-hidden="true" />)}
            </div>
          )}
          {data.status === "error" && (
            <div role="alert" className="space-y-2 rounded-card border border-danger-solid bg-danger-card p-4">
              <p className="font-bold text-danger-fg">{t("ex.error.title")}</p>
              <p>{apiErrorText(t, data.code)}</p>
              <button type="button" onClick={retry} className="min-h-11 rounded-control bg-brand px-4 font-bold text-white">{t("common.tryAgain")}</button>
            </div>
          )}
          {data.status === "ready" && shown.length === 0 && (
            <div className="rounded-card border border-dashed border-control-border bg-field p-4">
              <p className="font-bold">{status === "pending_review" ? t("ex.empty.title") : t("ex.empty.other")}</p>
              {status === "pending_review" && <p className="mt-1 text-ink-muted">{t("ex.empty.body")}</p>}
            </div>
          )}
          {data.status === "ready" && shown.length > 0 && (
            <ul className="space-y-2">
              {shown.map((r) => (
                <li key={r.case_id}>
                  <Link
                    href={href(status, r.case_id)}
                    aria-current={r.case_id === caseId ? "true" : undefined}
                    className={`block rounded-card border p-3 ${r.case_id === caseId ? "border-brand bg-brand-wash" : "border-line bg-surface"}`}
                  >
                    <span dir="auto" className="line-clamp-2 block font-bold">{r.question}</span>
                    <span className="block text-sm text-ink-muted">{formatDateTime(locale, r.created_at)}</span>
                    <span className="mt-1 flex flex-wrap gap-1 text-sm">
                      <span className="rounded-control bg-warning-bg px-2 text-warning-fg">{t(tagKey(r.escalation_reason_code))}</span>
                      <span className="rounded-control bg-sunken px-2">{r.district}</span>
                      <span className="rounded-control bg-info-bg px-2 text-info-fg">{t(`expert.status.${r.status}`)}</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-label={t("ex.review.title")}>
          {caseId ? (
            <CaseDetail key={caseId} caseId={caseId} onReviewed={reload} />
          ) : (
            <div className="rounded-card border border-dashed border-control-border bg-field p-6">
              <p className="font-bold">{t("ex.none.title")}</p>
              <p className="mt-1 text-ink-muted">{t("ex.none.body")}</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
