"use client";

import { useId, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { apiErrorText } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { ApiError, getApiClient } from "@/lib/api-client";
import { DEFAULT_DISTRICT, LIMITS } from "@/lib/checks/reference";
import { checkText } from "@/lib/checks/validate";
import { DistrictSelect } from "./DistrictSelect";
import { describedBy, Field, inputClass } from "./fields";
import { SubmitSheet, type SheetFailure } from "./SubmitSheet";

const EXAMPLES = ["weather", "advice", "expert", "safety"] as const;

/** Text-only entry point. One call; the backend's intent router decides what happens next (no photo is asked for here). */
export function QuestionForm() {
  const { t, locale } = useI18n();
  const router = useRouter();
  const id = useId();
  const [question, setQuestion] = useState("");
  const [district, setDistrict] = useState<string>(DEFAULT_DISTRICT);
  const [attempted, setAttempted] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [failure, setFailure] = useState<SheetFailure | null>(null);

  const problem = checkText(question, LIMITS.textMax, true);
  const error = attempted && problem ? t(`check.q.error.${problem}`, { max: LIMITS.textMax }) : null;

  async function send() {
    setFailure(null);
    setSheetOpen(true);
    try {
      const analysis = await getApiClient().askQuestion({ question: question.trim(), district, language: locale });
      router.push(`/checks/${analysis.case_id}/progress`);
    } catch (e) {
      setFailure({
        stepId: "question",
        message: apiErrorText(t, e instanceof ApiError ? e.code : "unknown"),
        saved: false,
        canSkip: false,
      });
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setAttempted(true);
    if (problem) {
      document.getElementById(`${id}-q`)?.focus();
      return;
    }
    void send();
  }

  return (
    <form onSubmit={onSubmit} noValidate className="max-w-3xl space-y-6">
      <p className="text-ink-muted">{t("check.question.intro")}</p>

      <Field
        id={`${id}-q`}
        label={t("check.q.label")}
        error={error}
        counter={t("check.describe.counter", { n: question.length, max: LIMITS.textMax })}
      >
        <textarea
          id={`${id}-q`}
          rows={4}
          value={question}
          placeholder={t("check.q.placeholder")}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(`${id}-q`, false, !!error)}
          onChange={(e) => setQuestion(e.target.value)}
          className={inputClass(!!error)}
        />
      </Field>

      <div>
        <p className="font-medium">{t("check.q.examples")}</p>
        <ul className="mt-2 flex flex-wrap gap-2">
          {EXAMPLES.map((key) => (
            <li key={key}>
              <button
                type="button"
                onClick={() => setQuestion(t(`check.q.example.${key}`))}
                className="min-h-11 rounded-control border border-control-border bg-surface px-3 text-start text-sm"
              >
                {t(`check.q.example.${key}`)}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <Field id={`${id}-district`} label={t("check.district.label")}>
        <DistrictSelect id={`${id}-district`} value={district} onChange={setDistrict} />
      </Field>

      <div className="space-y-2 rounded-card border border-line bg-warning-bg p-3 text-sm text-warning-fg">
        <p>{t("check.q.safety")}</p>
        <p>{t("check.q.photoNote")}</p>
      </div>

      <button type="submit" className="min-h-12 w-full rounded-control bg-brand px-4 font-bold text-white">
        {t("check.submit.question")}
      </button>

      <SubmitSheet
        open={sheetOpen}
        title={t("check.sheet.question")}
        steps={[{ id: "question", label: t("check.sheet.step.question") }]}
        activeId="question"
        failure={failure}
        onRetry={() => void send()}
        onSkip={() => undefined}
        onEdit={() => {
          setFailure(null);
          setSheetOpen(false);
        }}
      />
    </form>
  );
}
