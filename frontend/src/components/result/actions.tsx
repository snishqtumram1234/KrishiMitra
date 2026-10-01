"use client";

import { useId, useState } from "react";
import { useRouter } from "next/navigation";
import { apiErrorText, followUpOptionText, followUpQuestionText, qualityActionText } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { ApiError, getApiClient } from "@/lib/api-client";
import type { CaseAnalysisOut, FollowUpOptionCode, FollowUpQuestionId, ImageKind } from "@/lib/api-types";
import { FOLLOW_UP_OPTION_CODES, FOLLOW_UP_QUESTION_IDS } from "@/lib/api-types";
import { canRequestExpert, EXPERT_REQUEST_TEXT, nextAction } from "@/lib/checks/result";
import { LIMITS } from "@/lib/checks/reference";
import { checkText } from "@/lib/checks/validate";
import { PhotoCard, photoProblemText } from "@/components/checks/PhotoCard";
import { inputClass } from "@/components/checks/fields";
import { usePhoto } from "@/components/checks/usePhoto";

type FollowUpInput = { answer?: string; questionId?: string; option?: string; kind?: ImageKind; file?: Blob };

/** Sends a follow-up (`POST /follow-up`), which re-runs the orchestrator, then shows the new run's timeline. */
function useFollowUp(caseId: string) {
  const { t } = useI18n();
  const router = useRouter();
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function send(input: FollowUpInput) {
    setSending(true);
    setError(null);
    try {
      await getApiClient().followUp(caseId, input);
      router.push(`/checks/${caseId}/progress`);
    } catch (e) {
      setError(apiErrorText(t, e instanceof ApiError ? e.code : "unknown"));
      setSending(false);
    }
  }
  return { send, sending, error };
}

const primary = "min-h-12 rounded-control bg-brand px-4 font-bold text-white disabled:bg-brand-loading";
const known = <T extends string>(list: readonly T[], v: string): v is T => (list as readonly string[]).includes(v);

function ErrorLine({ id, text }: { id: string; text: string | null }) {
  return (
    <p id={id} role="alert" className="min-h-5 text-sm font-medium text-danger-fg">
      {text ?? ""}
    </p>
  );
}

// ---------------------------------------------------------------- a photo (replacement close-up, or a field photo)
function PhotoAnswer({ caseId, kind, title }: { caseId: string; kind: ImageKind; title: string }) {
  const { t, locale } = useI18n();
  const id = useId();
  const { photo, choose, clear } = usePhoto();
  const { send, sending, error } = useFollowUp(caseId);
  const [attempted, setAttempted] = useState(false);
  const problem = photoProblemText(t, locale, photo, attempted);
  const ready = photo?.check?.ok === true;
  return (
    <div className="space-y-3">
      <h3 className="font-bold">{title}</h3>
      <PhotoCard variant={kind === "leaf_closeup" ? "leaf" : "field"} photo={photo} problem={problem} onChoose={choose} onClear={clear} inputId={`${id}-photo`} />
      <ErrorLine id={`${id}-err`} text={error} />
      <button
        type="button"
        disabled={sending}
        className={primary}
        onClick={() => {
          setAttempted(true);
          if (ready && photo) void send({ kind, file: photo.file });
        }}
      >
        {sending ? t("next.sending") : t("next.photo.send")}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------- a structured or free-text answer
function AnswerForm({
  caseId,
  questionId,
  answerType,
  options,
  prompt,
}: {
  caseId: string;
  questionId: string | null;
  answerType: "choice" | "text";
  options: string[];
  prompt: string;
}) {
  const { t } = useI18n();
  const id = useId();
  const { send, sending, error } = useFollowUp(caseId);
  const [choice, setChoice] = useState("");
  const [text, setText] = useState("");
  const [problem, setProblem] = useState<string | null>(null);

  function submit() {
    const base = questionId ? { questionId } : {};
    if (answerType === "choice") {
      if (!choice) return setProblem(t("next.error.choose"));
      const detail = text.trim();
      if (checkText(text, LIMITS.textMax, false)) return setProblem(t("check.describe.error.tooLong", { max: LIMITS.textMax }));
      return void send({ ...base, option: choice, answer: detail || undefined });
    }
    const p = checkText(text, LIMITS.textMax, true);
    if (p) return setProblem(p === "required" ? t("next.error.empty") : t("check.describe.error.tooLong", { max: LIMITS.textMax }));
    void send({ ...base, answer: text.trim() });
  }

  return (
    <form
      noValidate
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        setProblem(null);
        submit();
      }}
    >
      <fieldset className="space-y-2">
        <legend className="font-bold">{prompt}</legend>
        {answerType === "choice" && (
          <div role="radiogroup" aria-label={t("next.choose")} className="flex flex-wrap gap-2">
            {options.map((code) => (
              <label key={code} className={`inline-flex min-h-11 cursor-pointer items-center rounded-control border px-3 ${choice === code ? "border-brand bg-brand-tint font-bold" : "border-control-border bg-surface"}`}>
                <input type="radio" name={`${id}-opt`} value={code} checked={choice === code} onChange={() => setChoice(code)} className="sr-only" />
                {known(FOLLOW_UP_OPTION_CODES, code) ? followUpOptionText(t, code as FollowUpOptionCode) : code}
              </label>
            ))}
          </div>
        )}
      </fieldset>
      <div>
        <label htmlFor={`${id}-text`} className="font-medium">
          {answerType === "choice" ? t("next.detail") : t("next.text.label")}
        </label>
        {answerType === "choice" ? (
          <input id={`${id}-text`} type="text" value={text} placeholder={t("next.detailPlaceholder")} onChange={(e) => setText(e.target.value)} className={inputClass(false)} />
        ) : (
          <textarea id={`${id}-text`} rows={3} value={text} onChange={(e) => setText(e.target.value)} className={inputClass(!!problem)} />
        )}
      </div>
      <ErrorLine id={`${id}-err`} text={problem ?? error} />
      <button type="submit" disabled={sending} className={primary}>
        {sending ? t("next.sending") : t("next.send")}
      </button>
    </form>
  );
}

// ---------------------------------------------------------------- "Next step"
export function NextStep({ caseId, analysis }: { caseId: string; analysis: CaseAnalysisOut }) {
  const { t } = useI18n();
  const action = nextAction(analysis);
  const [fieldOpen, setFieldOpen] = useState(false);
  const askedForPhoto = action.kind === "followUp" && action.options.answer_type === "photo";
  const offerField = analysis.missing_information.includes("field_overview_photo") && analysis.state === "PRELIMINARY_GUIDANCE" && !askedForPhoto;

  if (action.kind === "none" && !offerField) return null;

  return (
    <section className="space-y-4 rounded-card border-2 border-brand bg-brand-wash p-4">
      <h2 className="eyebrow">{t("next.title")}</h2>

      {action.kind === "photo" && (
        <div className="space-y-2">
          {action.tip && <p className="font-medium">{qualityActionText(t, action.tip)}</p>}
          <PhotoAnswer caseId={caseId} kind={action.photoKind} title={t("next.photo.leaf")} />
        </div>
      )}

      {action.kind === "followUp" && action.options.answer_type === "photo" && (
        <PhotoAnswer caseId={caseId} kind="field_overview" title={known(FOLLOW_UP_QUESTION_IDS, action.options.question_id) ? followUpQuestionText(t, action.options.question_id as FollowUpQuestionId) : t("next.photo.field")} />
      )}

      {action.kind === "followUp" && action.options.answer_type !== "photo" && (
        <AnswerForm
          caseId={caseId}
          questionId={action.options.question_id}
          answerType={action.options.answer_type === "choice" ? "choice" : "text"}
          options={action.options.options ?? []}
          prompt={known(FOLLOW_UP_QUESTION_IDS, action.options.question_id) ? followUpQuestionText(t, action.options.question_id as FollowUpQuestionId) : t("next.text.label")}
        />
      )}

      {action.kind === "expertAnswer" && (
        <AnswerForm caseId={caseId} questionId={null} answerType="text" options={[]} prompt={t("next.expertAnswer.title")} />
      )}

      {offerField && (
        <div>
          {fieldOpen ? (
            <PhotoAnswer caseId={caseId} kind="field_overview" title={t("next.photo.field")} />
          ) : (
            <button type="button" onClick={() => setFieldOpen(true)} className="min-h-12 rounded-control border border-control-border bg-surface px-4 font-medium">
              {t("next.photo.field")}
            </button>
          )}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------- "Request expert review"
export function ExpertRequest({ caseId, analysis }: { caseId: string; analysis: CaseAnalysisOut }) {
  const { t } = useI18n();
  const { send, sending, error } = useFollowUp(caseId);
  if (!canRequestExpert(analysis) || analysis.expert) return null;
  return (
    <section className="space-y-2">
      <p className="text-sm text-ink-muted">{t("expert.request.hint")}</p>
      <ErrorLine id="expert-err" text={error} />
      <button
        type="button"
        disabled={sending}
        onClick={() => void send({ answer: EXPERT_REQUEST_TEXT })}
        className="min-h-12 w-full rounded-control border-2 border-brand px-4 font-bold text-brand disabled:opacity-60"
      >
        {sending ? t("expert.requesting") : t("expert.request")}
      </button>
    </section>
  );
}
