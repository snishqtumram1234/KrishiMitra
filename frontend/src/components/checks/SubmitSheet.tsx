"use client";

import { useEffect, useRef } from "react";
import { useI18n } from "@/i18n/client";

export type SheetStep = { id: string; label: string };
export type SheetFailure = { stepId: string; message: string; saved: boolean; canSkip: boolean };

/**
 * The bottom sheet shown while a check is sent (design: "Sending your check"). A native modal <dialog>, so focus stays
 * inside and the page behind is inert. It cannot be dismissed while sending; after a failure it offers retry / edit.
 */
export function SubmitSheet({
  open,
  title,
  steps,
  activeId,
  failure,
  onRetry,
  onEdit,
  onSkip,
}: {
  open: boolean;
  title: string;
  steps: SheetStep[];
  activeId: string | null;
  failure: SheetFailure | null;
  onRetry: () => void;
  onEdit: () => void;
  onSkip: () => void;
}) {
  const { t } = useI18n();
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const activeIndex = steps.findIndex((s) => s.id === (failure?.stepId ?? activeId));

  return (
    <dialog
      ref={ref}
      aria-labelledby="sheet-title"
      onCancel={(e) => (failure ? onEdit() : e.preventDefault())}
      className="m-0 mt-auto w-full max-w-md rounded-t-sheet bg-surface p-5 text-ink backdrop:bg-black/50 sm:m-auto sm:rounded-sheet"
    >
      <h2 id="sheet-title" className="text-xl font-bold">
        {failure ? t("check.sheet.failed.title") : title}
      </h2>

      <ol className="mt-4 space-y-3">
        {steps.map((step, i) => {
          const status =
            failure && i === activeIndex ? "failed" : i < activeIndex ? "done" : i === activeIndex ? "active" : "waiting";
          return (
            <li key={step.id} className="flex items-center gap-3" aria-current={status === "active" ? "step" : undefined}>
              <span
                aria-hidden="true"
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white ${
                  status === "done" ? "bg-band-high" : status === "failed" ? "bg-danger-solid" : status === "active" ? "bg-info-fg" : "bg-disabled"
                }`}
              >
                {status === "done" ? "✓" : status === "failed" ? "!" : status === "active" ? "…" : ""}
              </span>
              <span className={status === "waiting" ? "text-ink-muted" : "font-medium"}>{step.label}</span>
              <span className="sr-only">{t(`check.sheet.status.${status}`)}</span>
            </li>
          );
        })}
      </ol>

      {failure ? (
        <div role="alert" className="mt-4 rounded-card bg-danger-bg p-3 text-danger-fg">
          <p className="font-medium">{failure.message}</p>
          <p className="mt-1 text-sm">{failure.saved ? t("check.sheet.failed.saved") : t("check.sheet.failed.notSaved")}</p>
        </div>
      ) : (
        <p role="status" className="mt-4 text-sm text-ink-muted">
          {t("check.sheet.keepOpen")}
        </p>
      )}

      {failure && (
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" onClick={onRetry} className="min-h-12 rounded-control bg-brand px-4 font-bold text-white">
            {t("check.sheet.retry")}
          </button>
          {failure.canSkip && (
            <button type="button" onClick={onSkip} className="min-h-12 rounded-control border border-control-border px-4 font-medium">
              {t("check.sheet.skipField")}
            </button>
          )}
          <button type="button" onClick={onEdit} className="min-h-12 px-3 font-medium text-brand underline">
            {t("check.sheet.edit")}
          </button>
        </div>
      )}
    </dialog>
  );
}
