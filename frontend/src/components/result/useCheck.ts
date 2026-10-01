"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, getApiClient, type ApiErrorCode } from "@/lib/api-client";
import type { CaseAnalysisOut, CaseOut } from "@/lib/api-types";

export type CheckState =
  | { status: "loading" }
  | { status: "notAnalyzed"; item: CaseOut }
  | { status: "error"; code: ApiErrorCode }
  | { status: "ready"; analysis: CaseAnalysisOut; item: CaseOut | null };

const codeOf = (e: unknown): ApiErrorCode => (e instanceof ApiError ? e.code : "unknown");

/**
 * Loads a case and its latest analysis (`GET /analysis`, identical in shape to what `analyze` returned), and can run the
 * analysis when it has never been run. `running` is true only while the real analyze request is in flight.
 */
export function useCheck(caseId: string) {
  const [state, setState] = useState<CheckState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    let current = true;
    const api = getApiClient();
    Promise.allSettled([api.latestAnalysis(caseId), api.getCase(caseId)]).then(([analysis, item]) => {
      if (!current) return;
      const caseOut = item.status === "fulfilled" ? item.value : null;
      if (analysis.status === "fulfilled") return setState({ status: "ready", analysis: analysis.value, item: caseOut });
      if (analysis.reason instanceof ApiError && analysis.reason.code === "not_found" && caseOut) {
        return setState({ status: "notAnalyzed", item: caseOut });
      }
      setState({ status: "error", code: item.status === "rejected" ? codeOf(item.reason) : codeOf(analysis.reason) });
    });
    return () => {
      current = false;
    };
  }, [caseId, attempt]);

  const reload = useCallback(() => {
    setState({ status: "loading" });
    setAttempt((n) => n + 1);
  }, []);

  const analyze = useCallback(async () => {
    setRunning(true);
    try {
      await getApiClient().analyzeCase(caseId);
      setState({ status: "loading" });
      setAttempt((n) => n + 1);
    } catch (e) {
      setState({ status: "error", code: codeOf(e) });
    } finally {
      setRunning(false);
    }
  }, [caseId]);

  return { state, running, reload, analyze };
}
