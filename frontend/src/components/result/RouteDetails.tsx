"use client";

import { useId, useState } from "react";
import { intentLabel, routeText, skippedReasonText, traceStepLabel } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/i18n/format";
import type { CaseAnalysisOut, RoutePath, SkippedReason, TraceStepId } from "@/lib/api-types";
import { ROUTE_PATHS, SKIPPED_REASONS, TRACE_STEP_IDS } from "@/lib/api-types";
import { timelineRows } from "@/lib/checks/result";

const isRoute = (v: string | null | undefined): v is RoutePath => !!v && (ROUTE_PATHS as readonly string[]).includes(v);
const isStep = (v: string): v is TraceStepId => (TRACE_STEP_IDS as readonly string[]).includes(v);
const isSkip = (v: string | null): v is SkippedReason => !!v && (SKIPPED_REASONS as readonly string[]).includes(v);

/** The "Route details" toggle: which question type, rule and path were used, the decision code, and every recorded step. */
export function RouteDetails({ analysis }: { analysis: CaseAnalysisOut }) {
  const { t, locale } = useI18n();
  const id = useId();
  const [open, setOpen] = useState(false);
  const r = analysis.result;
  const rows = timelineRows(analysis.trace);
  const code = [analysis.state, analysis.reason_code ? `${analysis.reason_code}${analysis.reason_detail ? `:${analysis.reason_detail}` : ""}` : null].filter(Boolean).join(" · ");
  const cost = (n: number) => t("timeline.cost", { cost: formatNumber(locale, n, { maximumFractionDigits: 6 }) });

  const facts: [string, string][] = [];
  if (r.intent) facts.push([t("route.question"), `${intentLabel(t, r.intent)}${r.intent_confidence != null ? ` · ${formatNumber(locale, r.intent_confidence, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : ""}`]);
  if (r.intent_rule) facts.push([t("route.rule"), r.intent_rule]);
  if (r.path) facts.push([t("route.path"), isRoute(r.path) ? `${r.path} · ${routeText(t, r.path)}` : r.path]);
  facts.push([t("route.decision"), code]);
  facts.push([t("route.total"), `${t("trace.latency", { ms: formatNumber(locale, r.total_latency_ms) })} · ${cost(r.total_cost_usd)}`]);

  return (
    <section className="rounded-card border border-line bg-surface">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={`${id}-panel`}
        onClick={() => setOpen((o) => !o)}
        className="flex min-h-12 w-full items-center justify-between gap-2 px-4 text-start font-bold"
      >
        {t("route.details")}
        <span aria-hidden="true">{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div id={`${id}-panel`} className="space-y-4 border-t border-line p-4">
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
            {facts.map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-ink-muted">{k}</dt>
                <dd className="break-words font-mono text-sm">{v}</dd>
              </div>
            ))}
          </dl>
          <div>
            <h3 className="eyebrow">{t("route.steps")}</h3>
            <ul className="mt-2 space-y-2">
              {rows.map((row) => (
                <li key={row.step} className="flex items-baseline justify-between gap-2">
                  <span className={row.tone === "skipped" ? "text-ink-muted" : ""}>
                    {isStep(row.step) ? traceStepLabel(t, row.step) : row.step}
                    {row.tone === "skipped" && (
                      <span className="block text-sm">{t("route.skipped")}{isSkip(row.skippedReason) ? ` · ${skippedReasonText(t, row.skippedReason)}` : ""}</span>
                    )}
                    {row.modelName && row.tone !== "skipped" && <span className="block font-mono text-xs text-ink-muted">{row.modelName}</span>}
                  </span>
                  {row.tone !== "skipped" && row.latencyMs != null && (
                    <span className="shrink-0 font-mono text-sm">{t("trace.latency", { ms: formatNumber(locale, row.latencyMs) })} · {cost(row.costUsd)}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </section>
  );
}
