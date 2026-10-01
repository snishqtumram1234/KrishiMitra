"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiErrorText, bandAria, missingCopy, reasonCopy, stateCopy } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { ApiError, getApiClient } from "@/lib/api-client";
import type { CaseAnalysisOut, CaseOut, MissingInformationCode } from "@/lib/api-types";
import { MISSING_INFORMATION_CODES } from "@/lib/api-types";

type Load =
  | { status: "loading" }
  | { status: "notAnalyzed" }
  | { status: "error"; code: ApiError["code"] }
  | { status: "ready"; analysis: CaseAnalysisOut; item: CaseOut | null };

const isMissingCode = (v: string): v is MissingInformationCode => (MISSING_INFORMATION_CODES as readonly string[]).includes(v);

/**
 * A deliberately small stand-in for the Result screen: only the state, the reason and the confidence band, built from
 * the structured fields. It exists so the New Check flow ends somewhere real. The full Result screen replaces it.
 */
export function ResultStub({ caseId }: { caseId: string }) {
  const { t } = useI18n();
  const [load, setLoad] = useState<Load>({ status: "loading" });

  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    const api = getApiClient();
    Promise.all([api.latestAnalysis(caseId), api.getCase(caseId).catch(() => null)]).then(
      ([analysis, item]) => current && setLoad({ status: "ready", analysis, item }),
      (e: unknown) => {
        if (!current) return;
        if (e instanceof ApiError && e.code === "not_found") setLoad({ status: "notAnalyzed" });
        else setLoad({ status: "error", code: e instanceof ApiError ? e.code : "unknown" });
      },
    );
    return () => {
      current = false;
    };
  }, [caseId, attempt]);

  const retry = () => {
    setLoad({ status: "loading" });
    setAttempt((n) => n + 1);
  };

  if (load.status === "loading") return <p role="status">{t("result.loading")}</p>;

  if (load.status === "notAnalyzed" || load.status === "error") {
    const failed = load.status === "error";
    return (
      <div role={failed ? "alert" : "status"} className="rounded-card border border-line bg-surface p-4">
        <h2 className="text-lg font-bold">{failed ? t("result.error.title") : t("result.notAnalyzed.title")}</h2>
        <p className="mt-1 text-ink-muted">{failed ? apiErrorText(t, load.code) : t("result.notAnalyzed.body")}</p>
        <p className="mt-3 text-sm">{t("safety.unavailable")}</p>
        {failed && (
          <button type="button" onClick={retry} className="mt-3 min-h-11 rounded-control bg-brand px-4 font-bold text-white">
            {t("common.tryAgain")}
          </button>
        )}
      </div>
    );
  }

  const { analysis, item } = load;
  const state = stateCopy(t, analysis.state);
  const reason = analysis.reason_code
    ? reasonCopy(t, analysis.reason_code, analysis.reason_detail, { district: item?.district })
    : null;
  const missing = analysis.missing_information.filter(isMissingCode);

  return (
    <article className="space-y-5">
      <h2 className="text-title font-bold">{state.label}</h2>
      <p className="text-ink-muted">{state.summary}</p>

      {item && (
        <div>
          <p className="eyebrow">{t("result.question")}</p>
          <p dir="auto">{item.symptom_context}</p>
        </div>
      )}

      {reason && (
        <section className="rounded-card border border-line bg-surface p-4">
          <h3 className="font-bold">{reason.title}</h3>
          <p className="mt-1">{reason.body}</p>
        </section>
      )}

      {analysis.confidence_band && <p className="font-medium">{bandAria(t, analysis.confidence_band)}</p>}

      {missing.length > 0 && (
        <section>
          <h3 className="font-bold">{t("result.missing.title")}</h3>
          <ul className="mt-2 list-disc ps-5">
            {missing.map((code) => (
              <li key={code}>
                {missingCopy(t, code).title}
                <span className="block text-sm text-ink-muted">{missingCopy(t, code).hint}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {analysis.result.path === "image_diagnosis" && (
        <p className="rounded-card bg-warning-bg p-3 text-sm text-warning-fg">{t("safety.preliminary")}</p>
      )}
      <p className="text-sm text-ink-muted">{t("result.notBuilt")}</p>
      <Link href="/checks/new" className="inline-flex min-h-12 items-center rounded-control bg-brand px-4 font-bold text-white">
        {t("result.another")}
      </Link>
    </article>
  );
}
