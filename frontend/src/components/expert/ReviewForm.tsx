"use client";

import { useId, useRef, useState, type FormEvent } from "react";
import { apiErrorText, categoryLabel } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { ApiError, getApiClient } from "@/lib/api-client";
import type { Category, ExpertReviewRecord, ReviewDecision } from "@/lib/api-types";
import { buildReview, checkReview, DECISIONS, FIELD_MAX, NOTES_MAX, REVIEW_CATEGORIES, type ReviewInput } from "@/lib/expert";
import { ErrorSummary, inputClass } from "@/components/checks/fields";

const EMPTY: ReviewInput = { decision: "", label: "", notes: "", advisoryTitle: "", advisoryPublisher: "", advisoryUrl: "" };

/** The expert's review of one pending escalation (`POST /api/expert/cases/{id}/review`). */
export function ReviewForm({ caseId, onSent }: { caseId: string; onSent: (record: ExpertReviewRecord) => void }) {
  const { t } = useI18n();
  const id = useId();
  const [input, setInput] = useState<ReviewInput>(EMPTY);
  const [attempted, setAttempted] = useState(false);
  const [sending, setSending] = useState(false);
  const [failure, setFailure] = useState<{ text: string; conflict: boolean } | null>(null);
  const summaryRef = useRef<HTMLDivElement>(null);
  const set = <K extends keyof ReviewInput>(k: K, v: ReviewInput[K]) => setInput((s) => ({ ...s, [k]: v }));

  const problems = checkReview(input);
  const text = (k: keyof typeof problems) => {
    const p = problems[k];
    if (!attempted || !p) return null;
    return p === "notesLong" ? t("ex.review.err.notesLong", { max: NOTES_MAX }) : t(`ex.review.err.${p}`);
  };
  const targets: Record<string, string> = { decision: `${id}-decision`, label: `${id}-label`, notes: `${id}-notes`, advisory: `${id}-adv-title`, url: `${id}-adv-url` };
  const summary = attempted ? (Object.keys(problems) as (keyof typeof problems)[]).map((k) => ({ targetId: targets[k], text: text(k) ?? "" })) : [];

  async function submit(e: FormEvent) {
    e.preventDefault();
    setAttempted(true);
    setFailure(null);
    if (Object.keys(problems).length > 0) {
      setTimeout(() => summaryRef.current?.focus(), 0);
      return;
    }
    setSending(true);
    try {
      onSent(await getApiClient().reviewExpertCase(caseId, buildReview(input)));
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "unknown";
      setFailure({ text: code === "conflict" ? t("ex.review.err.conflict") : apiErrorText(t, code), conflict: code === "conflict" });
      setSending(false);
    }
  }

  const decision = input.decision;
  const moves = decision === "request_more" ? "awaiting_farmer" : "reviewed";
  const lengthNote = `${input.notes.length} / ${NOTES_MAX}`;

  return (
    <form onSubmit={submit} noValidate className="space-y-4 rounded-card border border-line bg-surface p-4">
      <h3 className="text-lg font-bold">{t("ex.review.title")}</h3>
      <ErrorSummary summaryRef={summaryRef} title={t("ex.review.summary")} items={summary} />

      <fieldset>
        <legend className="font-medium">{t("ex.review.decision")}</legend>
        <div id={`${id}-decision`} tabIndex={-1} className="mt-2 grid gap-2 sm:grid-cols-2">
          {DECISIONS.map((d: ReviewDecision) => (
            <label key={d} className={`block cursor-pointer rounded-card border p-3 ${decision === d ? "border-brand bg-brand-wash" : "border-control-border bg-field"}`}>
              <input type="radio" name={`${id}-d`} value={d} checked={decision === d} onChange={() => set("decision", d)} className="sr-only" />
              <span className="block font-bold">{t(`expert.decision.${d}`)}</span>
              <span className="block text-sm text-ink-muted">{t(`expert.decision.${d}.hint`)}</span>
            </label>
          ))}
        </div>
        {text("decision") && <p className="mt-1 text-sm text-danger-fg">{text("decision")}</p>}
      </fieldset>

      <div>
        <label htmlFor={`${id}-label`} className="font-medium">{t("ex.review.category")}</label>
        <select
          id={`${id}-label`}
          value={input.label}
          disabled={decision !== "likely"}
          aria-invalid={text("label") ? true : undefined}
          onChange={(e) => set("label", e.target.value as Category | "")}
          className={inputClass(!!text("label"))}
        >
          <option value="">{decision === "likely" ? t("ex.review.category.choose") : t("ex.review.category.only")}</option>
          {REVIEW_CATEGORIES.map((c) => (
            <option key={c} value={c}>{categoryLabel(t, c)}</option>
          ))}
        </select>
        {text("label") && <p className="mt-1 text-sm text-danger-fg">{text("label")}</p>}
      </div>

      <div>
        <label htmlFor={`${id}-notes`} className="font-medium">{t("ex.review.notes")}</label>
        <textarea
          id={`${id}-notes`}
          rows={5}
          value={input.notes}
          aria-invalid={text("notes") ? true : undefined}
          aria-describedby={`${id}-warn`}
          onChange={(e) => set("notes", e.target.value)}
          className={inputClass(!!text("notes"))}
        />
        <div className="flex justify-between gap-2 text-sm">
          <p className="text-danger-fg">{text("notes") ?? ""}</p>
          <p className="shrink-0 text-ink-muted">{lengthNote}</p>
        </div>
        <p id={`${id}-warn`} className="mt-1 rounded-control bg-warning-bg p-2 text-sm text-warning-fg">{t("ex.review.notes.warning")}</p>
      </div>

      <fieldset className="space-y-2">
        <legend className="font-medium">{t("ex.review.advisory")}</legend>
        {text("advisory") && <p className="text-sm text-danger-fg">{text("advisory")}</p>}
        <div className="grid gap-2 sm:grid-cols-3">
          {([["advisoryTitle", "adv-title", "ex.review.adv.title"], ["advisoryPublisher", "adv-pub", "ex.review.adv.publisher"], ["advisoryUrl", "adv-url", "ex.review.adv.link"]] as const).map(([key, suffix, label]) => (
            <div key={key}>
              <label htmlFor={`${id}-${suffix}`} className="text-sm">{t(label)}</label>
              <input
                id={`${id}-${suffix}`}
                type={key === "advisoryUrl" ? "url" : "text"}
                maxLength={key === "advisoryUrl" ? 500 : FIELD_MAX}
                value={input[key]}
                aria-invalid={key === "advisoryUrl" && text("url") ? true : undefined}
                onChange={(e) => set(key, e.target.value)}
                className={inputClass(key === "advisoryUrl" ? !!text("url") : !!text("advisory"))}
              />
            </div>
          ))}
        </div>
        {text("url") && <p className="text-sm text-danger-fg">{text("url")}</p>}
      </fieldset>

      {failure && (
        <div role="alert" className="space-y-2 rounded-card bg-danger-bg p-3 text-danger-fg">
          <p>{failure.text}</p>
          {failure.conflict && (
            <button type="button" onClick={() => window.location.reload()} className="min-h-11 rounded-control border border-danger-solid px-3 font-medium">
              {t("ex.reload")}
            </button>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" disabled={sending} className="min-h-12 rounded-control bg-brand px-4 font-bold text-white disabled:bg-brand-loading">
          {sending ? t("ex.review.sending") : decision === "request_more" ? t("ex.review.submit.request_more") : t("ex.review.submit")}
        </button>
        {decision && <p className="text-sm text-ink-muted">{t(`ex.review.moves.${moves}`)}</p>}
      </div>
    </form>
  );
}
