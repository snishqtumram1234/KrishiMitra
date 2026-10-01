"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { apiErrorText, intentLabel, stateCopy, traceStepLabel } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { formatDateTime, formatNumber } from "@/i18n/format";
import { ApiError, getApiClient, type ApiErrorCode } from "@/lib/api-client";
import type { CostLatencyOut, Overview, RoutesOut, TraceStepId } from "@/lib/api-types";
import { TRACE_STEP_IDS } from "@/lib/api-types";
import { allStates, allTiers, dominantState, isTier, ms, percent, rateParts, usd, WINDOWS, type WindowDays } from "@/lib/metrics";
import { CHART, GroupBars, HBar } from "./charts";

type Res<T> = { status: "loading" } | { status: "error"; code: ApiErrorCode } | { status: "ready"; data: T };
const isStep = (v: string): v is TraceStepId => (TRACE_STEP_IDS as readonly string[]).includes(v);
const card = "rounded-card border border-line bg-surface p-4";

/** One metrics endpoint. Each of the three loads on its own, so one failing does not hide the others. */
function useResource<T>(load: () => Promise<T>, key: string, attempt: number): Res<T> {
  const [res, setRes] = useState<{ key: string; value: Res<T> }>({ key, value: { status: "loading" } });
  useEffect(() => {
    let current = true;
    load().then(
      (data) => current && setRes({ key, value: { status: "ready", data } }),
      (e: unknown) => current && setRes({ key, value: { status: "error", code: e instanceof ApiError ? e.code : "unknown" } }),
    );
    return () => {
      current = false;
    };
    // `load` is rebuilt every render; `key` (window + attempt) is what actually identifies the request
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, attempt]);
  return res.key === key ? res.value : { status: "loading" };
}

function Failed({ code, onRetry }: { code: ApiErrorCode; onRetry: () => void }) {
  const { t } = useI18n();
  return (
    <div role="alert" className="space-y-2 rounded-card border border-danger-solid bg-danger-card p-4">
      <p className="font-bold text-danger-fg">{t("m.error.title")}</p>
      <p>{apiErrorText(t, code)}</p>
      <button type="button" onClick={onRetry} className="min-h-11 rounded-control bg-brand px-4 font-bold text-white">{t("common.tryAgain")}</button>
    </div>
  );
}

function Loading({ h = 32 }: { h?: number }) {
  return <div aria-hidden="true" style={{ height: h * 4 }} className="animate-pulse rounded-card bg-skeleton" />;
}

function Kpi({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className={card}>
      <p className="eyebrow">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
      <p className="text-sm text-ink-muted">{sub}</p>
    </div>
  );
}

function Table({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[28rem] text-sm">
        <thead>
          <tr className="text-ink-muted">{head.map((h) => <th key={h} scope="col" className="py-1 pe-3 text-start font-medium">{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-line">
              {r.map((c, j) => <td key={j} className="py-1 pe-3 align-top">{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function MetricsDashboard({ days }: { days: WindowDays | undefined }) {
  const { t, locale } = useI18n();
  const [attempt, setAttempt] = useState(0);
  const key = `${days ?? "all"}`;
  const api = getApiClient();
  const overview = useResource<Overview>(() => api.metricsOverview(days), `o${key}`, attempt);
  const routes = useResource<RoutesOut>(() => api.metricsRoutes(days), `r${key}`, attempt);
  const cost = useResource<CostLatencyOut>(() => api.metricsCostLatency(days), `c${key}`, attempt);
  const retry = () => setAttempt((n) => n + 1);

  const windowLabel = days ? t(`m.window.${days}`) : t("m.window.all");
  const href = (d: WindowDays | undefined) => (d ? `/metrics?days=${d}` : "/metrics");
  const empty = overview.status === "ready" && overview.data.total_analyses === 0;

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-title font-bold">{t("m.title")}</h1>
        <p className="text-ink-muted" aria-live="polite">
          {overview.status === "ready"
            ? t("m.subtitle", { window: windowLabel, analyses: formatNumber(locale, overview.data.total_analyses), cases: formatNumber(locale, overview.data.total_cases), when: formatDateTime(locale, overview.data.window.generated_at) })
            : overview.status === "loading" ? t("m.loading") : windowLabel}
        </p>
        <nav aria-label={t("m.window.label")} className="flex flex-wrap gap-2">
          {([...WINDOWS, undefined] as (WindowDays | undefined)[]).map((d) => (
            <Link key={d ?? "all"} href={href(d)} aria-current={d === days ? "page" : undefined} className={`inline-flex min-h-11 items-center rounded-control border px-3 text-sm font-medium ${d === days ? "border-brand bg-brand text-white" : "border-control-border bg-surface"}`}>
              {d ? t(`m.window.${d}`) : t("m.window.all")}
            </Link>
          ))}
        </nav>
      </header>

      {/* ---------------------------------------------------------------- headline numbers */}
      {overview.status === "loading" && <div aria-busy="true" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{[0, 1, 2, 3, 4].map((i) => <Loading key={i} h={24} />)}</div>}
      {overview.status === "error" && <Failed code={overview.code} onRetry={retry} />}
      {overview.status === "ready" && (() => {
        const o = overview.data;
        const lat = o.latency_per_analysis;
        const esc = rateParts(o.escalation_rate), abs = rateParts(o.abstention_rate), va = rateParts(o.vision_abstention_rate), rr = rateParts(o.retrieval_success_rate), ch = rateParts(o.cache_hit_rate);
        const sources = Object.entries(o.weather_sources).map(([k, v]) => `${k} ${v}`).join(", ") || "—";
        return (
          <>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              <Kpi label={t("m.kpi.analyses")} value={formatNumber(locale, o.total_analyses)} sub={t("m.kpi.analyses.sub", { n: formatNumber(locale, o.total_cases) })} />
              <Kpi label={t("m.kpi.latency")} value={lat.n ? `${ms(locale, lat.p50_ms)} / ${ms(locale, lat.p95_ms)}` : "—"} sub={lat.n ? t("m.kpi.latency.sub", { avg: ms(locale, lat.avg_ms, 1), max: ms(locale, lat.max_ms) }) : t("m.kpi.latency.none")} />
              <Kpi label={t("m.kpi.costCase")} value={usd(locale, o.cost_per_case_usd)} sub={t("m.kpi.costCase.sub", { total: usd(locale, o.cost_total_usd) })} />
              <Kpi label={t("m.kpi.escalation")} value={percent(locale, o.escalation_rate.rate)} sub={t("m.kpi.escalation.sub", { num: esc.num, den: esc.den })} />
              <Kpi label={t("m.kpi.abstention")} value={percent(locale, o.abstention_rate.rate)} sub={t("m.kpi.abstention.sub", { num: abs.num, den: abs.den })} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Kpi label={t("m.kpi.visionAbstain")} value={percent(locale, o.vision_abstention_rate.rate)} sub={t("m.kpi.visionAbstain.sub", { num: va.num, den: va.den })} />
              <Kpi label={t("m.kpi.retrieval")} value={percent(locale, o.retrieval_success_rate.rate)} sub={t("m.kpi.retrieval.sub", { num: rr.num, den: rr.den })} />
              <Kpi label={t("m.kpi.cache")} value={percent(locale, o.cache_hit_rate.rate)} sub={t("m.kpi.cache.sub", { num: ch.num, den: ch.den, sources })} />
              <Kpi label={t("m.kpi.disagree")} value={formatNumber(locale, o.model_disagreement_count)} sub={t("m.kpi.disagree.sub")} />
            </div>
          </>
        );
      })()}

      {empty && (
        <div className="space-y-2 rounded-card border border-dashed border-control-border bg-field p-5 text-center">
          <p className="text-lg font-bold">{t("m.empty.title")}</p>
          <p className="text-ink-muted">{t("m.empty.body")}</p>
          {days && <Link href="/metrics" className="inline-flex min-h-11 items-center rounded-control bg-brand px-4 font-bold text-white">{t("m.empty.cta")}</Link>}
        </div>
      )}

      {/* ---------------------------------------------------------------- routes and decision states */}
      {!empty && (
        <div className="grid gap-4 lg:grid-cols-2">
          <section className={`${card} space-y-3`}>
            <h2 className="text-lg font-bold">{t("m.routes.title")}</h2>
            {routes.status === "loading" && <Loading />}
            {routes.status === "error" && <Failed code={routes.code} onRetry={retry} />}
            {routes.status === "ready" && (() => {
              const r = routes.data;
              const v = rateParts(r.vision_call_rate);
              return (
                <>
                  <HBar caption={t("m.routes.chart")} data={r.by_path.map((p) => ({ name: p.path, value: Math.round(p.share * 100) }))} format={(n) => `${n}%`} max={100} />
                  <Table
                    head={[t("m.col.path"), t("m.col.count"), t("m.col.latency"), t("m.col.cost"), t("m.col.outcome")]}
                    rows={r.by_path.map((p) => {
                      const top = dominantState(p.decision_states);
                      return [<code key="p" className="font-mono text-xs">{p.path}</code>, formatNumber(locale, p.count), ms(locale, p.avg_latency_ms, 1), usd(locale, p.avg_cost_usd), top ? stateCopy(t, top).badge : "—"];
                    })}
                  />
                  <p className="text-sm text-ink-muted">{t("m.routes.visionCalled", { num: v.num, den: v.den })}</p>
                  {Object.keys(r.by_intent).length > 0 && (
                    <p className="text-sm text-ink-muted">{t("m.byIntent")}: {Object.entries(r.by_intent).map(([k, n]) => `${intentLabel(t, k)} ${n}`).join(" · ")}</p>
                  )}
                </>
              );
            })()}
          </section>

          <section className={`${card} space-y-3`}>
            <h2 className="text-lg font-bold">{t("m.states.title")}</h2>
            {routes.status === "loading" && <Loading />}
            {routes.status === "error" && <Failed code={routes.code} onRetry={retry} />}
            {routes.status === "ready" && (
              <HBar caption={t("m.states.chart")} data={allStates(routes.data.by_decision_state).map((s) => ({ name: stateCopy(t, s.state).label, value: s.count }))} format={(n) => formatNumber(locale, n)} color={CHART.info} />
            )}
          </section>
        </div>
      )}

      {/* ---------------------------------------------------------------- cost and latency */}
      {!empty && (
        <section className={`${card} space-y-3`}>
          <h2 className="text-lg font-bold">{t("m.steps.title")}</h2>
          {cost.status === "loading" && <Loading />}
          {cost.status === "error" && <Failed code={cost.code} onRetry={retry} />}
          {cost.status === "ready" && (
            <>
              <GroupBars
                caption={t("m.steps.chart")}
                data={cost.data.by_step.map((s) => ({ name: isStep(s.step) ? traceStepLabel(t, s.step) : s.step, p50: s.latency.p50_ms ?? 0, p95: s.latency.p95_ms ?? 0 }))}
                series={[{ key: "p50", label: t("m.series.p50"), color: CHART.brand }, { key: "p95", label: t("m.series.p95"), color: CHART.soil }]}
                format={(n) => ms(locale, n)}
              />
              <Table
                head={[t("m.col.step"), t("m.col.tier"), t("m.col.calls"), t("m.col.errors"), t("m.col.p50"), t("m.col.p95"), t("m.col.total"), t("m.col.avg")]}
                rows={cost.data.by_step.map((s) => [
                  <span key="s">{isStep(s.step) ? traceStepLabel(t, s.step) : s.step}<code className="block font-mono text-xs text-ink-muted">{s.step}</code></span>,
                  isTier(s.tier) ? t(`m.tier.${s.tier}`) : s.tier,
                  formatNumber(locale, s.calls), formatNumber(locale, s.errors), ms(locale, s.latency.p50_ms), ms(locale, s.latency.p95_ms), usd(locale, s.total_cost_usd), usd(locale, s.avg_cost_usd),
                ])}
              />
            </>
          )}
        </section>
      )}

      {!empty && (
        <div className="grid gap-4 lg:grid-cols-2">
          <section className={`${card} space-y-3`}>
            <h2 className="text-lg font-bold">{t("m.tiers.title")}</h2>
            {cost.status === "loading" && <Loading />}
            {cost.status === "error" && <Failed code={cost.code} onRetry={retry} />}
            {cost.status === "ready" && (() => {
              const tiers = allTiers(cost.data.by_tier);
              return (
                <>
                  <GroupBars
                    caption={t("m.tiers.chart")}
                    data={tiers.map(({ tier, row }) => ({ name: t(`m.tier.${tier}`), calls: Math.round((row?.share_of_calls ?? 0) * 100), cost: Math.round((row?.share_of_cost ?? 0) * 100) }))}
                    series={[{ key: "calls", label: t("m.tiers.calls"), color: CHART.brand }, { key: "cost", label: t("m.tiers.cost"), color: CHART.soil }]}
                    format={(n) => `${n}%`}
                  />
                  <Table
                    head={[t("m.col.tier"), t("m.col.calls"), t("m.tiers.calls"), t("m.col.total"), t("m.tiers.cost")]}
                    rows={tiers.map(({ tier, row }) => [t(`m.tier.${tier}`), row && row.calls > 0 ? formatNumber(locale, row.calls) : t("m.tier.none"), percent(locale, row?.share_of_calls), usd(locale, row?.total_cost_usd ?? 0), percent(locale, row?.share_of_cost)])}
                  />
                </>
              );
            })()}
          </section>

          <section className={`${card} space-y-3`}>
            <h2 className="text-lg font-bold">{t("m.skipped.title")}</h2>
            {(routes.status === "loading" || cost.status === "loading") && <Loading />}
            {routes.status === "error" && <Failed code={routes.code} onRetry={retry} />}
            {routes.status === "ready" && (() => {
              const skipped = Object.entries(routes.data.skipped_steps);
              return (
                <>
                  <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1">
                    <dt className="text-ink-muted">{t("m.skipped.saved")}</dt>
                    <dd className="text-end font-bold">{usd(locale, routes.data.estimated_cost_saved_usd)}</dd>
                    {cost.status === "ready" && cost.data.cost_if_vision_always_ran_usd != null && (
                      <>
                        <dt className="text-ink-muted">{t("m.skipped.ifVision")}</dt>
                        <dd className="text-end font-bold">
                          {usd(locale, cost.data.cost_if_vision_always_ran_usd)}
                          <span className="block text-xs font-normal text-ink-muted">{t("m.skipped.vsActual", { actual: usd(locale, cost.data.cost_total_usd) })}</span>
                        </dd>
                      </>
                    )}
                  </dl>
                  {skipped.length === 0 ? <p className="text-ink-muted">{t("m.skipped.none")}</p> : (
                    <HBar caption={t("m.skipped.title")} data={skipped.map(([k, n]) => ({ name: isStep(k) ? traceStepLabel(t, k) : k, value: n }))} format={(n) => t("m.skipped.times", { n: formatNumber(locale, n) })} color={CHART.warning} />
                  )}
                </>
              );
            })()}
          </section>
        </div>
      )}

      {overview.status === "ready" && (overview.data.notes ?? []).length > 0 && (
        <section className={card}>
          <h2 className="eyebrow">{t("m.notes.title")}</h2>
          <ul className="mt-2 list-disc space-y-1 ps-5">{overview.data.notes!.map((n) => <li key={n}>{n}</li>)}</ul>
          <p className="mt-2 text-xs text-ink-muted">{t("m.notes.source")}</p>
        </section>
      )}
      <p className="text-sm text-ink-muted">{t("m.honest")}</p>
    </div>
  );
}
