"use client";

import Link from "next/link";
import { apiErrorText, growthStageText, reasonCopy, routeText, stateCopy } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/i18n/format";
import type { RoutePath } from "@/lib/api-types";
import { ROUTE_PATHS } from "@/lib/api-types";
import { checkIsSafe, timelineRows } from "@/lib/checks/result";
import { Timeline } from "./Timeline";
import { useCheck } from "./useCheck";

const isRoute = (v: string | null | undefined): v is RoutePath => !!v && (ROUTE_PATHS as readonly string[]).includes(v);

/**
 * Replays the RECORDED trace of the latest analysis. `analyze` is synchronous and returns everything at once, so there is
 * no live half-finished state to show: while we wait there is only an honest "starting" state with no invented steps,
 * and once the recorded run is here the whole timeline is shown, with the real step names and latencies.
 */
export function AnalysisProgress({ caseId }: { caseId: string }) {
  const { t, locale } = useI18n();
  const { state, running, reload, analyze } = useCheck(caseId);

  if (state.status === "loading" || running) {
    return (
      <div className="space-y-4" aria-busy="true">
        <p className="inline-block rounded-control bg-info-bg px-2 py-1 text-sm font-medium text-info-fg">{t("common.loading")}</p>
        <h2 className="text-lg font-bold">{running ? t("progress.running") : t("progress.starting.title")}</h2>
        <p role="status" className="text-ink-muted">{t("progress.starting.body")}</p>
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-10 animate-pulse rounded-card bg-skeleton" aria-hidden="true" />
        ))}
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div role="alert" className="space-y-3 rounded-card border border-danger-solid bg-danger-card p-4">
        <h2 className="text-lg font-bold text-danger-fg">{t("result.error.title")}</h2>
        <p>{apiErrorText(t, state.code)}</p>
        {checkIsSafe(state.code) && <p className="text-sm">{t("result.error.saved")}</p>}
        <p className="text-sm">{t("safety.unavailable")}</p>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={reload} className="min-h-11 rounded-control bg-brand px-4 font-bold text-white">
            {t("common.tryAgain")}
          </button>
          <Link href="/dashboard" className="inline-flex min-h-11 items-center px-3 font-medium text-brand underline">
            {t("result.toDashboard")}
          </Link>
        </div>
      </div>
    );
  }

  if (state.status === "notAnalyzed") {
    return (
      <div className="space-y-3 rounded-card border border-dashed border-control-border bg-field p-4">
        <h2 className="text-lg font-bold">{t("result.notAnalyzed.title")}</h2>
        <p className="text-ink-muted">{t("result.notAnalyzed.body")}</p>
        <button type="button" onClick={() => void analyze()} className="min-h-12 rounded-control bg-brand px-4 font-bold text-white">
          {t("progress.run")}
        </button>
      </div>
    );
  }

  const { analysis, item } = state;
  const rows = timelineRows(analysis.trace);
  const copy = stateCopy(t, analysis.state);
  const reason = analysis.reason_code ? reasonCopy(t, analysis.reason_code, analysis.reason_detail, { district: item?.district }) : null;
  const path = analysis.result.path;
  const card =
    analysis.state === "NEEDS_BETTER_IMAGE"
      ? "border-warning-accent bg-warning-bg text-warning-fg"
      : analysis.state === "EXPERT_REVIEW"
        ? "border-info-fg bg-info-bg text-info-fg"
        : "border-line bg-surface";

  return (
    <div className="space-y-6">
      <p className="inline-block rounded-control bg-info-bg px-2 py-1 text-sm font-medium text-info-fg">{copy.badge}</p>

      {item && (
        <div className="rounded-card border border-line bg-surface p-4">
          <p dir="auto" className="font-medium">{item.symptom_context}</p>
          <p className="text-sm text-ink-muted">{[item.district, growthStageText(t, item.growth_stage) || null].filter(Boolean).join(" · ")}</p>
        </div>
      )}

      <section>
        <p className="eyebrow">{t("route.label")}{isRoute(path) && <> · <code className="font-mono normal-case">{path}</code></>}</p>
        {isRoute(path) && <p className="mt-1">{routeText(t, path)}</p>}
        <p className="mt-1 text-sm text-ink-muted">{t("progress.recorded")}</p>
      </section>

      <Timeline rows={rows} />
      <p className="font-mono text-sm text-ink-muted">{t("progress.total", { ms: formatNumber(locale, analysis.result.total_latency_ms) })}</p>

      {reason && analysis.state !== "PRELIMINARY_GUIDANCE" && (
        <div className={`rounded-card border p-4 ${card}`}>
          <p className="font-bold">{reason.title}</p>
          <p className="mt-1">{reason.body}</p>
        </div>
      )}

      <Link href={`/checks/${caseId}`} className="inline-flex min-h-12 w-full items-center justify-center rounded-control bg-brand px-4 font-bold text-white">
        {t("progress.seeResult")}
      </Link>
    </div>
  );
}
