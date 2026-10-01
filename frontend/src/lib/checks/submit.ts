/**
 * The crop-check submission: create the case, upload the photo(s), then analyse. It is resumable. `progress` records what
 * already succeeded, so after a failure "Try again" continues from the failed step instead of creating a second case or
 * uploading a photo twice.
 */
import type { ApiClient } from "../api-client";
import type { CaseAnalysisOut, CaseCreate, ImageKind } from "../api-types";

export type SubmitStep = "details" | "leaf" | "field" | "analyze";

export type CropSubmission = {
  case: CaseCreate;
  leaf: Blob;
  field: Blob | null;
};

export type SubmitProgress = {
  caseId: string | null;
  uploaded: Set<ImageKind>;
  /** The farmer chose to go on without the optional field photo after it failed. */
  skipField: boolean;
};

export const newProgress = (): SubmitProgress => ({ caseId: null, uploaded: new Set(), skipField: false });

/** The steps this submission will run, in order. */
export function stepsFor(submission: Pick<CropSubmission, "field">, progress?: Pick<SubmitProgress, "skipField">): SubmitStep[] {
  const steps: SubmitStep[] = ["details", "leaf"];
  if (submission.field && !progress?.skipField) steps.push("field");
  steps.push("analyze");
  return steps;
}

export class SubmitFailure extends Error {
  constructor(
    readonly step: SubmitStep,
    readonly cause: unknown,
  ) {
    super(`Submission failed at ${step}`);
  }
}

type Api = Pick<ApiClient, "createCase" | "uploadImage" | "analyzeCase">;

export async function submitCropCheck(
  api: Api,
  submission: CropSubmission,
  progress: SubmitProgress,
  onStep: (step: SubmitStep) => void,
  signal?: AbortSignal,
): Promise<CaseAnalysisOut> {
  const run = async <T>(step: SubmitStep, fn: () => Promise<T>): Promise<T> => {
    onStep(step);
    try {
      return await fn();
    } catch (error) {
      throw new SubmitFailure(step, error);
    }
  };

  if (!progress.caseId) {
    const created = await run("details", () => api.createCase(submission.case));
    progress.caseId = created.id;
  }
  const caseId = progress.caseId;

  if (!progress.uploaded.has("leaf_closeup")) {
    await run("leaf", () => api.uploadImage(caseId, { kind: "leaf_closeup", file: submission.leaf }));
    progress.uploaded.add("leaf_closeup");
  }
  if (submission.field && !progress.skipField && !progress.uploaded.has("field_overview")) {
    const file = submission.field;
    await run("field", () => api.uploadImage(caseId, { kind: "field_overview", file }));
    progress.uploaded.add("field_overview");
  }
  return run("analyze", () => api.analyzeCase(caseId, signal));
}
