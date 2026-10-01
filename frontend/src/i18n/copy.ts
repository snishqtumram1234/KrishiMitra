/**
 * Builds user-facing copy from the API's STRUCTURED fields. The backend's English `message` and `follow_up_question`
 * are never read here, so every screen reads the same in English and Marathi. Each builder takes a translator `t`.
 *
 * The template-literal keys below are checked by the compiler: if the API gains a state, reason code, band, etc. and
 * en.ts has no matching key, `tsc` fails here instead of a screen showing a raw key at runtime.
 */
import type { ApiErrorCode } from "@/lib/api-client";
import type {
  Category,
  Intent,
  ConfidenceBand,
  DecisionState,
  FollowUpOptionCode,
  FollowUpQuestionId,
  MissingInformationCode,
  QualityIssue,
  QualityNextAction,
  ReasonCode,
  RoutePath,
  SkippedReason,
  SourceFailure,
  TraceStatus,
  TraceStepId,
  WeatherSource,
} from "@/lib/api-types";
import { MESSAGES, type MessageKey, type Translator } from "./translate";

export function stateCopy(t: Translator, state: DecisionState) {
  return {
    label: t(`state.${state}.label`),
    badge: t(`state.${state}.badge`),
    summary: t(`state.${state}.summary`),
  };
}

export function bandLabel(t: Translator, band: ConfidenceBand): string {
  return t(`band.${band}.label`);
}
export function bandAria(t: Translator, band: ConfidenceBand): string {
  return t("band.aria", { band: bandLabel(t, band) });
}
export function bandExplanation(t: Translator, band: ConfidenceBand): string {
  return t(`band.${band}.explain`);
}

export function categoryLabel(t: Translator, category: Category): string {
  return t(`category.${category}`);
}

export function qualityIssueText(t: Translator, issue: QualityIssue): string {
  return t(`quality.issue.${issue}`);
}
export function qualityActionText(t: Translator, action: QualityNextAction): string {
  return t(`quality.action.${action}`);
}

export function missingCopy(t: Translator, code: MissingInformationCode) {
  return { title: t(`missing.${code}.title`), hint: t(`missing.${code}.hint`) };
}

export function followUpQuestionText(t: Translator, id: FollowUpQuestionId): string {
  return t(`followUp.question.${id}`);
}
export function followUpOptionText(t: Translator, code: FollowUpOptionCode): string {
  return t(`followUp.option.${code}`);
}

export function traceStepLabel(t: Translator, step: TraceStepId): string {
  return t(`trace.step.${step}`);
}
export function traceStatusLabel(t: Translator, status: TraceStatus): string {
  return t(`trace.status.${status}`);
}
export function skippedReasonText(t: Translator, reason: SkippedReason): string {
  return t(`trace.skipped.${reason}`);
}

export function routeText(t: Translator, path: RoutePath): string {
  return t(`route.${path}`);
}

export function weatherSourceLabel(t: Translator, source: WeatherSource | "stale"): string {
  return t(`weather.source.${source}`);
}

/**
 * Title and body for a decision. `detail` is `reason_detail`: a quality issue for quality_failed, a source failure
 * for sources_unavailable. `params` supplies {district} for the weather reason.
 */
export function reasonCopy(
  t: Translator,
  code: ReasonCode,
  detail?: string | null,
  params: { district?: string } = {},
): { title: string; body: string } {
  switch (code) {
    case "quality_failed": {
      const tip = detail && isQualityIssue(detail) ? qualityIssueText(t, detail) : "";
      return { title: t("reason.quality_failed.title"), body: t("reason.quality_failed.body", { tip }).trim() };
    }
    case "sources_unavailable": {
      const key = `reason.sources_unavailable.${detail && isSourceFailure(detail) ? detail : "unknown"}` as MessageKey;
      return { title: t("reason.sources_unavailable.title"), body: t(key) };
    }
    case "weather_context":
      return {
        title: t("reason.weather_context.title", { district: params.district ?? "" }),
        body: t("reason.weather_context.body"),
      };
    default:
      return { title: t(`reason.${code}.title`), body: t(`reason.${code}.body`) };
  }
}

const QUALITY_ISSUE_SET: ReadonlySet<string> = new Set<QualityIssue>([
  "missing_image",
  "unreadable_image",
  "too_small",
  "too_dark",
  "too_bright",
  "blurry",
  "no_leaf_detected",
]);
const SOURCE_FAILURE_SET: ReadonlySet<string> = new Set<SourceFailure>([
  "advisory",
  "weather",
  "vision_error",
  "quality_gate_error",
  "intent_router_error",
]);
export const isQualityIssue = (v: string): v is QualityIssue => QUALITY_ISSUE_SET.has(v);
export const isSourceFailure = (v: string): v is SourceFailure => SOURCE_FAILURE_SET.has(v);

const ERROR_KEYS: Record<ApiErrorCode, MessageKey> = {
  network: "error.network",
  timeout: "error.timeout",
  aborted: "error.unknown",
  unauthorized: "error.unauthorized",
  forbidden: "error.forbidden",
  not_found: "error.notFound",
  conflict: "error.conflict",
  payload_too_large: "error.tooLarge",
  unsupported_media: "error.unsupportedMedia",
  invalid: "error.invalid",
  unavailable: "error.unavailable",
  server: "error.server",
  unknown: "error.unknown",
};

/** Text for an ApiError. Uses its `code`, never the server's English `detail`. */
export function apiErrorText(t: Translator, code: ApiErrorCode): string {
  return t(ERROR_KEYS[code]);
}

export function intentLabel(t: Translator, intent: Intent | string | null | undefined): string {
  if (!intent) return "";
  const key = `intent.${intent}` as MessageKey;
  return key in MESSAGES.en ? t(key) : intent;
}

/** A stored growth stage: a known code gets its translated label; anything else the farmer or an old client stored is shown as written. */
export function growthStageText(t: Translator, value: string | null | undefined): string {
  if (!value) return "";
  const key = `growthStage.${value}` as MessageKey;
  return key in MESSAGES.en ? t(key) : value;
}

/** The short status badge for a check in a list. A check that was never analysed has no decision state yet. */
export function checkBadge(t: Translator, state: DecisionState | null | undefined): string {
  return state ? t(`state.${state}.badge`) : t("state.none.badge");
}
