"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiErrorText, checkBadge, growthStageText } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { formatDateTime } from "@/i18n/format";
import { ApiError, getApiClient, type ApiErrorCode } from "@/lib/api-client";
import type { CaseOut, DecisionState, WeatherResult } from "@/lib/api-types";
import { DEFAULT_DISTRICT } from "@/lib/checks/reference";
import { WeatherCard } from "@/components/result/parts";

/** How many checks the list shows. The API returns all of them (it has no paging yet). */
const SHOWN = 20;

type Checks = { status: "loading" } | { status: "error"; code: ApiErrorCode } | { status: "ready"; items: CaseOut[] };
type Weather = { status: "loading" } | { status: "error" } | { status: "ready"; data: WeatherResult };

const codeOf = (e: unknown): ApiErrorCode => (e instanceof ApiError ? e.code : "unknown");

const BADGE_TONE: Record<DecisionState | "none", string> = {
  NEEDS_BETTER_IMAGE: "bg-warning-bg text-warning-fg",
  NEEDS_MORE_CONTEXT: "bg-warning-bg text-warning-fg",
  PRELIMINARY_GUIDANCE: "bg-success-bg text-success-fg",
  EXPERT_REVIEW: "bg-info-bg text-info-fg",
  UNSUPPORTED: "bg-sunken text-ink",
  none: "bg-sunken text-ink-muted",
};

function Skeleton({ h }: { h: number }) {
  return <div style={{ height: h * 4 }} className="animate-pulse rounded-card bg-skeleton" aria-hidden="true" />;
}

export function Dashboard() {
  const { t, locale } = useI18n();
  const [checks, setChecks] = useState<Checks>({ status: "loading" });
  const [weather, setWeather] = useState<Weather>({ status: "loading" });
  const [checksAttempt, setChecksAttempt] = useState(0);
  const [weatherAttempt, setWeatherAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    getApiClient().listCases().then(
      (items) => current && setChecks({ status: "ready", items }),
      (e: unknown) => current && setChecks({ status: "error", code: codeOf(e) }),
    );
    return () => {
      current = false;
    };
  }, [checksAttempt]);

  // The weather is for the district of the newest check (there is no "my district" setting yet), else the default.
  const settled = checks.status !== "loading";
  const district = checks.status === "ready" && checks.items[0]?.district ? checks.items[0].district : DEFAULT_DISTRICT;
  useEffect(() => {
    if (!settled) return;
    let current = true;
    getApiClient().getWeather(district).then(
      (data) => current && setWeather({ status: "ready", data }),
      () => current && setWeather({ status: "error" }),
    );
    return () => {
      current = false;
    };
  }, [settled, district, weatherAttempt]);

  const retryChecks = () => {
    setChecks({ status: "loading" });
    setChecksAttempt((n) => n + 1);
  };
  const retryWeather = () => {
    setWeather({ status: "loading" });
    setWeatherAttempt((n) => n + 1);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-title font-bold">{t("dashboard.title")}</h1>

      <div className="space-y-2">
        <Link href="/checks/new" className="block rounded-card bg-brand p-4 text-white">
          <span className="block text-lg font-bold">{t("dashboard.newCheck.title")}</span>
          <span className="block text-sm">{t("dashboard.newCheck.sub")}</span>
        </Link>
        <Link href="/checks/new?mode=question" className="inline-flex min-h-11 items-center font-medium text-brand underline">
          {t("dashboard.ask")}
        </Link>
      </div>

      {weather.status === "loading" && (
        <div aria-busy="true" className="space-y-2">
          <p role="status" className="text-sm text-ink-muted">{t("dashboard.weather.loading")}</p>
          <Skeleton h={30} />
        </div>
      )}
      {weather.status === "error" && (
        <div role="alert" className="rounded-card border border-line bg-surface p-4">
          <p>{t("dashboard.weather.failed")}</p>
          <button type="button" onClick={retryWeather} className="mt-2 min-h-11 rounded-control border border-control-border px-3 font-medium">
            {t("common.tryAgain")}
          </button>
        </div>
      )}
      {weather.status === "ready" && <WeatherCard weather={weather.data} district={district} />}

      {checks.status === "loading" && (
        <div aria-busy="true" className="space-y-3">
          <p role="status" className="text-ink-muted">{t("dashboard.loading")}</p>
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} h={20} />
          ))}
        </div>
      )}

      {checks.status === "error" && (
        <div role="alert" className="space-y-2 rounded-card border border-danger-solid bg-danger-card p-4">
          <h2 className="text-lg font-bold text-danger-fg">{t("dashboard.error.title")}</h2>
          <p>{apiErrorText(t, checks.code)}</p>
          <p className="text-sm">{t("dashboard.error.body")}</p>
          <button type="button" onClick={retryChecks} className="min-h-11 rounded-control bg-brand px-4 font-bold text-white">
            {t("common.tryAgain")}
          </button>
        </div>
      )}

      {checks.status === "ready" && checks.items.length === 0 && (
        <div className="space-y-3 rounded-card border border-dashed border-control-border bg-field p-5 text-center">
          <h2 className="text-lg font-bold">{t("dashboard.empty.title")}</h2>
          <p className="text-ink-muted">{t("dashboard.empty.body")}</p>
          <Link href="/checks/new" className="inline-flex min-h-12 items-center rounded-control bg-brand px-4 font-bold text-white">
            {t("dashboard.empty.cta")}
          </Link>
        </div>
      )}

      {checks.status === "ready" && checks.items.length > 0 && (
        <section>
          <h2 className="eyebrow">{t("dashboard.recent", { count: checks.items.length })}</h2>
          <ul className="mt-2 space-y-3">
            {checks.items.slice(0, SHOWN).map((c) => {
              const state = c.decision_state ?? null;
              const meta = [c.district, c.growth_stage ? growthStageText(t, c.growth_stage) : null, formatDateTime(locale, c.created_at)]
                .filter(Boolean)
                .join(" · ");
              return (
                <li key={c.id}>
                  <Link href={`/checks/${c.id}`} className="block rounded-card border border-line bg-surface p-4">
                    <span dir="auto" className="line-clamp-2 block font-bold">{c.symptom_context}</span>
                    <span className={`mt-1 inline-block rounded-control px-2 py-0.5 text-sm font-medium ${BADGE_TONE[state ?? "none"]}`}>
                      {checkBadge(t, state)}
                    </span>
                    <span className="mt-1 block text-sm text-ink-muted">{meta}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
          {checks.items.length > SHOWN && <p className="mt-2 text-sm text-ink-muted">{t("dashboard.showing", { n: SHOWN })}</p>}
        </section>
      )}
    </div>
  );
}
