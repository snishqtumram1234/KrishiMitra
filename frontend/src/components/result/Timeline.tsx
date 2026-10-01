"use client";

import { bandLabel, intentLabel, skippedReasonText, traceStepLabel, weatherSourceLabel } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/i18n/format";
import type { SkippedReason, TraceStepId, WeatherSource } from "@/lib/api-types";
import { SKIPPED_REASONS, TRACE_STEP_IDS } from "@/lib/api-types";
import type { TimelineRow } from "@/lib/checks/result";
import { stateCopy } from "@/i18n/copy";
import type { DecisionState } from "@/lib/api-types";

const isStepId = (v: string): v is TraceStepId => (TRACE_STEP_IDS as readonly string[]).includes(v);
const isSkipped = (v: string | null): v is SkippedReason => !!v && (SKIPPED_REASONS as readonly string[]).includes(v);

const ICON: Record<TimelineRow["tone"], { glyph: string; cls: string }> = {
  done: { glyph: "✓", cls: "bg-band-high text-white" },
  stopped: { glyph: "!", cls: "bg-warning-fg text-white" },
  failed: { glyph: "✕", cls: "bg-danger-solid text-white" },
  skipped: { glyph: "", cls: "border-2 border-dashed border-control-border bg-surface" },
  decided: { glyph: "✓", cls: "bg-info-fg text-white" },
};

/** The recorded steps of one run, as the backend returned them: real step names, real latencies, real skip reasons. */
export function Timeline({ rows }: { rows: TimelineRow[] }) {
  const { t, locale } = useI18n();

  const detailLine = (row: TimelineRow): string | null => {
    const d = row.detail;
    switch (row.step) {
      case "intent_router":
        return d.intent
          ? t("timeline.intent", { intent: intentLabel(t, d.intent), confidence: formatNumber(locale, d.confidence ?? 0, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) })
          : null;
      case "quality_gate":
        return d.score == null ? null : t(d.passed === false ? "timeline.quality.failed" : "timeline.quality.passed", { score: formatNumber(locale, Math.round(d.score)) });
      case "vision":
        return d.band
          ? t("timeline.vision", { band: bandLabel(t, d.band), confidence: formatNumber(locale, d.confidence ?? 0, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) })
          : null;
      case "advisory":
        return d.sourceCount
          ? t("timeline.advisory.some", { count: d.sourceCount, verified: d.verifiedCount ?? 0, demo: d.demoCount ?? 0 })
          : t("timeline.advisory.none");
      case "weather":
        return d.weatherSource ? t("timeline.weather", { source: weatherSourceLabel(t, d.weatherSource as WeatherSource) }) : null;
      case "policy_decision":
        return d.state ? t("timeline.policy", { state: stateCopy(t, d.state as DecisionState).label }) : null;
      default:
        return null;
    }
  };

  return (
    <ol aria-label={t("timeline.label")} className="space-y-4">
      {rows.map((row) => {
        const icon = ICON[row.tone];
        const label = isStepId(row.step) ? traceStepLabel(t, row.step) : row.step;
        const detail = detailLine(row);
        const matched = row.step === "intent_router" ? row.detail.matched : undefined;
        return (
          <li key={row.step} className="flex gap-3">
            <span aria-hidden="true" className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-sm font-bold ${icon.cls}`}>
              {icon.glyph}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2">
                <p className={`font-medium ${row.tone === "skipped" ? "text-ink-muted line-through" : ""}`}>
                  {label}
                  <span className="sr-only"> · {t(`trace.status.${row.status}`)}</span>
                </p>
                {row.latencyMs != null && row.tone !== "decided" && (
                  <p className="shrink-0 font-mono text-sm text-ink-muted">{t("trace.latency", { ms: formatNumber(locale, row.latencyMs) })}</p>
                )}
              </div>
              {row.tone === "skipped" && (
                <p className="text-sm text-ink-muted">{isSkipped(row.skippedReason) ? skippedReasonText(t, row.skippedReason) : t("trace.status.skipped")}</p>
              )}
              {detail && row.tone !== "skipped" && <p className="text-sm">{detail}</p>}
              {matched && matched.length > 0 && (
                <p className="text-sm text-ink-muted">{t("timeline.matched", { words: matched.join(", ") })}</p>
              )}
              {row.tone === "stopped" && <p className="text-sm font-medium text-warning-fg">{t("progress.stopped")}</p>}
              {row.modelName && row.tone !== "skipped" && <p className="font-mono text-xs text-ink-muted">{`${row.step} · ${row.modelName}`}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
