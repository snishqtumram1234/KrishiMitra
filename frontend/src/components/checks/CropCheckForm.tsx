"use client";

import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { apiErrorText } from "@/i18n/copy";
import { useI18n } from "@/i18n/client";
import { formatDate } from "@/i18n/format";
import { ApiError, getApiClient } from "@/lib/api-client";
import type { CaseCreate } from "@/lib/api-types";
import {
  DEFAULT_DISTRICT,
  GROWTH_STAGES,
  LIMITS,
} from "@/lib/checks/reference";
import {
  newProgress,
  stepsFor,
  submitCropCheck,
  SubmitFailure,
  type SubmitProgress,
  type SubmitStep,
} from "@/lib/checks/submit";
import {
  checkCropForm,
  todayInIndia,
  type CropFormProblems,
} from "@/lib/checks/validate";
import { daysBefore, loadDemoPhoto, type DemoSample } from "@/lib/checks/demo";
import { DemoPicker } from "./DemoPicker";
import { DistrictSelect } from "./DistrictSelect";
import {
  describedBy,
  ErrorSummary,
  Field,
  inputClass,
  Section,
} from "./fields";
import { PhotoCard, photoProblemText } from "./PhotoCard";
import { SubmitSheet, type SheetFailure } from "./SubmitSheet";
import { usePhoto } from "./usePhoto";

export function CropCheckForm() {
  const { t, locale } = useI18n();
  const router = useRouter();
  const id = useId();
  const leaf = usePhoto();
  const field = usePhoto();

  const [description, setDescription] = useState("");
  const [district, setDistrict] = useState<string>(DEFAULT_DISTRICT);
  const [stage, setStage] = useState("");
  const [startedAt, setStartedAt] = useState("");
  const [rainfall, setRainfall] = useState("");
  const [more, setMore] = useState("");

  const [demoBusy, setDemoBusy] = useState<string | null>(null);
  const [attempted, setAttempted] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [activeStep, setActiveStep] = useState<SubmitStep | null>(null);
  const [failure, setFailure] = useState<SheetFailure | null>(null);
  const [skipField, setSkipField] = useState(false);
  const progress = useRef<SubmitProgress>(newProgress());
  const summaryRef = useRef<HTMLDivElement>(null);
  const today = todayInIndia();

  const leafOk = leaf.photo?.check?.ok === true;
  const problems: CropFormProblems = checkCropForm(
    { description, startedAt, rainfall, more },
    leafOk,
    today,
  );
  const leafProblem = photoProblemText(t, locale, leaf.photo, attempted);
  const fieldProblem = photoProblemText(t, locale, field.photo, false);
  const fieldBlocked = field.photo?.check ? !field.photo.check.ok : false;

  const text = {
    describe:
      problems.describe &&
      t(`check.describe.error.${problems.describe as "required" | "tooLong"}`, {
        max: LIMITS.textMax,
      }),
    started:
      problems.started &&
      t(`check.started.error.${problems.started as "future" | "invalid"}`, {
        today: formatDate(locale, today),
      }),
    rain:
      problems.rain &&
      t("check.rain.error.tooLong", { max: LIMITS.rainfallMax }),
    more:
      problems.more && t("check.more.error.tooLong", { max: LIMITS.textMax }),
  };
  // Errors appear once the farmer has tried to submit (or, for the photos, as soon as a bad file is chosen).
  const show = (v: string | false | undefined) => (attempted && v ? v : null);

  const summary: { targetId: string; text: string }[] = [];
  if (leafProblem && (attempted || leaf.photo)) {
    const c = leaf.photo?.check;
    const kind = !leaf.photo ? "missing" : c && !c.ok ? c.problem : "missing";
    summary.push({
      targetId: `${id}-leaf`,
      text: t(`check.photo.summary.${kind}`),
    });
  }
  if (fieldProblem)
    summary.push({ targetId: `${id}-field`, text: t("check.field.summary") });
  if (attempted && text.describe)
    summary.push({
      targetId: `${id}-describe`,
      text: t("check.describe.summary"),
    });
  if (attempted && text.started)
    summary.push({
      targetId: `${id}-started`,
      text: t("check.started.summary"),
    });
  if (attempted && text.rain)
    summary.push({ targetId: `${id}-rain`, text: t("check.rain.summary") });
  if (attempted && text.more)
    summary.push({ targetId: `${id}-more`, text: t("check.more.summary") });

  const [focusSummary, setFocusSummary] = useState(0);
  useEffect(() => {
    if (focusSummary > 0) summaryRef.current?.focus();
  }, [focusSummary]);

  function currentSubmission() {
    const body: CaseCreate = {
      crop: "soybean",
      district,
      symptom_context: description.trim(),
      language: locale,
      growth_stage: stage || null,
      symptom_started_at: startedAt || null,
      recent_rainfall: rainfall.trim() || null,
      description: more.trim() || null,
    };
    return {
      case: body,
      leaf: leaf.photo!.file,
      field: field.photo && !fieldBlocked ? field.photo.file : null,
    };
  }

  async function run(prepared?: ReturnType<typeof currentSubmission>) {
    setFailure(null);
    setSheetOpen(true);
    const submission = prepared ?? currentSubmission();
    try {
      const analysis = await submitCropCheck(
        getApiClient(),
        submission,
        progress.current,
        setActiveStep,
      );
      router.push(`/checks/${analysis.case_id}/progress`);
    } catch (error) {
      if (!(error instanceof SubmitFailure)) throw error;
      const cause = error.cause;
      setFailure({
        stepId: error.step,
        message: apiErrorText(
          t,
          cause instanceof ApiError ? cause.code : "unknown",
        ),
        saved: progress.current.caseId !== null,
        canSkip: error.step === "field",
      });
    }
  }

  /** Demo: show a sample photo and example answers in the form, pause briefly so they can be seen, then run the check. */
  async function runDemo(sample: DemoSample) {
    setDemoBusy(sample.id);
    try {
      const file = await loadDemoPhoto(sample);
      const startedOn = daysBefore(today, sample.daysAgo);
      const texts = {
        describe: t(`check.demo.${sample.id}.describe`),
        rain: t(`check.demo.${sample.id}.rain`),
        more: t(`check.demo.${sample.id}.more`),
      };
      void leaf.choose(file);
      field.clear();
      setDescription(texts.describe);
      setDistrict(DEFAULT_DISTRICT);
      setStage(sample.stage);
      setStartedAt(startedOn);
      setRainfall(texts.rain);
      setMore(texts.more);
      await new Promise((resolve) => setTimeout(resolve, 1200));
      progress.current = newProgress();
      setSkipField(false);
      await run({
        case: {
          crop: "soybean",
          district: DEFAULT_DISTRICT,
          symptom_context: texts.describe,
          language: locale,
          growth_stage: sample.stage,
          symptom_started_at: startedOn,
          recent_rainfall: texts.rain,
          description: texts.more,
        },
        leaf: file,
        field: null,
      });
    } catch {
      setFailure({ stepId: "details", message: apiErrorText(t, "unknown"), saved: false, canSkip: false });
      setSheetOpen(true);
    } finally {
      setDemoBusy(null);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setAttempted(true);
    const blocked =
      Object.keys(problems).length > 0 ||
      fieldBlocked ||
      leaf.photo?.check === null;
    if (blocked) {
      setFocusSummary((n) => n + 1);
      return;
    }
    progress.current = newProgress();
    setSkipField(false);
    void run();
  }

  const sheetSteps = stepsFor(
    { field: fieldBlocked ? null : (field.photo?.file ?? null) },
    { skipField },
  ).map((step) => ({
    id: step,
    label: t(`check.sheet.step.${step}`),
  }));

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-8">
      <p className="text-ink-muted">{t("check.crop.intro")}</p>
      <DemoPicker busyId={demoBusy} disabled={demoBusy !== null || sheetOpen} onPick={(s) => void runDemo(s)} />
      <ErrorSummary
        summaryRef={summaryRef}
        title={
          summary.length === 1
            ? t("check.errors.summaryOne")
            : t("check.errors.summaryMany", { count: summary.length })
        }
        items={summary}
      />

      <div className="grid gap-8 lg:grid-cols-2 lg:items-start lg:gap-x-12">
        <div className="space-y-8">
          <Section title={t("check.photo.step")} badge={t("check.required")}>
            <PhotoCard
              variant="leaf"
              photo={leaf.photo}
              problem={leafProblem}
              onChoose={leaf.choose}
              onClear={leaf.clear}
              inputId={`${id}-leaf`}
            />
            <div className="text-sm text-ink-muted">
              <p className="font-medium">{t("check.photo.tips")}</p>
              <ul className="list-disc ps-5">
                <li>{t("check.photo.tip.daylight")}</li>
                <li>{t("check.photo.tip.steady")}</li>
                <li>{t("check.photo.tip.frame")}</li>
              </ul>
            </div>
          </Section>

          <Section title={t("check.field.step")} badge={t("check.optional")}>
            <PhotoCard
              variant="field"
              photo={field.photo}
              problem={fieldProblem}
              onChoose={field.choose}
              onClear={field.clear}
              inputId={`${id}-field`}
            />
          </Section>

          <Section title={t("check.describe.step")}>
            <Field
              id={`${id}-describe`}
              label={t("check.describe.label")}
              error={show(text.describe)}
              counter={t("check.describe.counter", {
                n: description.length,
                max: LIMITS.textMax,
              })}
            >
              <textarea
                id={`${id}-describe`}
                rows={4}
                value={description}
                placeholder={t("check.describe.placeholder")}
                aria-invalid={show(text.describe) ? true : undefined}
                aria-describedby={describedBy(
                  `${id}-describe`,
                  false,
                  !!show(text.describe),
                )}
                onChange={(e) => setDescription(e.target.value)}
                className={inputClass(!!show(text.describe))}
              />
            </Field>
          </Section>
        </div>
        <div className="space-y-8">
          <Section title={t("check.place.step")}>
            <div>
              <p className="font-medium">{t("check.crop.label")}</p>
              <p className="mt-1 min-h-12 rounded-control border border-line bg-sunken px-3 py-3">
                {t("check.crop.soybean")}
              </p>
            </div>
            <Field id={`${id}-district`} label={t("check.district.label")}>
              <DistrictSelect
                id={`${id}-district`}
                value={district}
                onChange={setDistrict}
              />
            </Field>
            <p className="text-sm text-ink-muted">{t("check.place.note")}</p>
          </Section>

          <Section title={t("check.details.step")} badge={t("check.optional")}>
            <Field id={`${id}-stage`} label={t("check.stage.label")}>
              <select
                id={`${id}-stage`}
                value={stage}
                onChange={(e) => setStage(e.target.value)}
                className={inputClass(false)}
              >
                <option value="">{t("check.stage.choose")}</option>
                {GROWTH_STAGES.map((code) => (
                  <option key={code} value={code}>
                    {t(`growthStage.${code}`)}
                  </option>
                ))}
              </select>
            </Field>
            <Field
              id={`${id}-started`}
              label={t("check.started.label")}
              error={show(text.started)}
            >
              <input
                id={`${id}-started`}
                type="date"
                max={today}
                value={startedAt}
                aria-invalid={show(text.started) ? true : undefined}
                aria-describedby={describedBy(
                  `${id}-started`,
                  false,
                  !!show(text.started),
                )}
                onChange={(e) => setStartedAt(e.target.value)}
                className={inputClass(!!show(text.started))}
              />
            </Field>
            <Field
              id={`${id}-rain`}
              label={t("check.rain.label")}
              error={show(text.rain)}
            >
              <input
                id={`${id}-rain`}
                type="text"
                value={rainfall}
                placeholder={t("check.rain.placeholder")}
                aria-invalid={show(text.rain) ? true : undefined}
                aria-describedby={describedBy(
                  `${id}-rain`,
                  false,
                  !!show(text.rain),
                )}
                onChange={(e) => setRainfall(e.target.value)}
                className={inputClass(!!show(text.rain))}
              />
            </Field>
            <Field
              id={`${id}-more`}
              label={t("check.more.label")}
              hint={t("check.more.hint")}
              error={show(text.more)}
            >
              <textarea
                id={`${id}-more`}
                rows={3}
                value={more}
                placeholder={t("check.more.placeholder")}
                aria-invalid={show(text.more) ? true : undefined}
                aria-describedby={describedBy(
                  `${id}-more`,
                  true,
                  !!show(text.more),
                )}
                onChange={(e) => setMore(e.target.value)}
                className={inputClass(!!show(text.more))}
              />
            </Field>
          </Section>

          <button
            type="submit"
            className="min-h-12 w-full rounded-control bg-brand px-4 font-bold text-white"
          >
            {t("check.submit.crop")}
          </button>
        </div>
      </div>

      <SubmitSheet
        open={sheetOpen}
        title={t("check.sheet.crop")}
        steps={sheetSteps}
        activeId={activeStep}
        failure={failure}
        onRetry={() => void run()}
        onSkip={() => {
          progress.current.skipField = true;
          setSkipField(true);
          void run();
        }}
        onEdit={() => {
          // Editing may change what was saved, so the next submit starts a fresh case rather than reusing this one.
          progress.current = newProgress();
          setSkipField(false);
          setFailure(null);
          setSheetOpen(false);
        }}
      />
    </form>
  );
}
