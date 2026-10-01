"use client";

import { useRef } from "react";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/i18n/format";
import type { Translator } from "@/i18n/translate";
import type { PhotoState } from "./usePhoto";

type Variant = "leaf" | "field";

export function formatBytes(t: Translator, locale: "en" | "mr", bytes: number): string {
  const mb = bytes / (1024 * 1024);
  const one = { maximumFractionDigits: 1 };
  return mb >= 1
    ? t("check.photo.sizeMb", { n: formatNumber(locale, mb, one) })
    : t("check.photo.sizeKb", { n: formatNumber(locale, Math.max(1, Math.round(bytes / 1024))) });
}

/** The problem text for a photo, or null when it is fine. `missing` is the "nothing chosen" error after a submit attempt. */
export function photoProblemText(
  t: Translator,
  locale: "en" | "mr",
  photo: PhotoState | null,
  missing: boolean,
): string | null {
  if (!photo) return missing ? t("check.photo.error.missing") : null;
  const c = photo.check;
  if (!c || c.ok) return null;
  if (c.problem === "tooLarge") {
    return t("check.photo.error.tooLarge", { size: formatNumber(locale, photo.file.size / (1024 * 1024), { maximumFractionDigits: 1 }) });
  }
  return t(`check.photo.error.${c.problem}`);
}

export function PhotoCard({
  variant,
  photo,
  problem,
  onChoose,
  onClear,
  inputId,
}: {
  variant: Variant;
  photo: PhotoState | null;
  problem: string | null;
  onChoose: (file: File) => void;
  onClear: () => void;
  /** id of the primary button, so the error summary can move focus to it */
  inputId: string;
}) {
  const { t, locale } = useI18n();
  const galleryRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const bad = !!problem;
  const reading = photo !== null && photo.check === null;
  const describedBy = problem ? `${inputId}-problem` : undefined;

  const pick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // choosing the same file again must still fire
    if (file) onChoose(file);
  };
  const button = "min-h-11 rounded-control border border-control-border bg-surface px-3 font-medium text-ink";

  return (
    <div
      className={`rounded-card border p-4 ${
        bad ? "border-danger-solid bg-danger-card" : photo ? "border-line bg-surface" : "border-dashed border-control-border bg-field"
      }`}
    >
      <input ref={galleryRef} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" tabIndex={-1} aria-hidden="true" onChange={pick} />
      <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="sr-only" tabIndex={-1} aria-hidden="true" onChange={pick} />

      {photo ? (
        <div className="flex gap-3">
          {photo.file.type.startsWith("image/") ? (
            // eslint-disable-next-line @next/next/no-img-element -- a local blob: preview, not an optimisable asset
            <img src={photo.previewUrl} alt={t("check.photo.alt")} className="h-20 w-20 shrink-0 rounded-control object-cover" />
          ) : (
            <div className="h-20 w-20 shrink-0 rounded-control bg-sunken" aria-hidden="true" />
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium" dir="auto">
              {photo.file.name}
            </p>
            <p className="text-sm text-ink-muted">
              {photo.check?.ok
                ? t("check.photo.meta", { type: photo.check.type, size: formatBytes(t, locale, photo.file.size) })
                : formatBytes(t, locale, photo.file.size)}
            </p>
            <p className={`mt-1 inline-block rounded-control px-2 text-sm font-medium ${bad ? "bg-danger-bg text-danger-fg" : "bg-success-bg text-success-fg"}`}>
              {reading ? t("check.photo.reading") : bad ? t("check.photo.notUploaded") : t("check.photo.ready")}
            </p>
          </div>
        </div>
      ) : (
        <div className="text-center">
          <p className="font-medium">{variant === "leaf" ? t("check.photo.empty") : t("check.field.add")}</p>
          <p className="mt-1 text-sm text-ink-muted">{variant === "leaf" ? t("check.photo.hint") : t("check.field.hint")}</p>
        </div>
      )}

      {problem && (
        <p id={describedBy} className="mt-3 text-sm font-medium text-danger-fg">
          {problem}
        </p>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {variant === "leaf" && (
          <button type="button" id={inputId} aria-describedby={describedBy} onClick={() => cameraRef.current?.click()} className={button}>
            {photo ? t("check.photo.retake") : t("check.photo.take")}
          </button>
        )}
        <button
          type="button"
          id={variant === "leaf" ? undefined : inputId}
          aria-describedby={describedBy}
          onClick={() => galleryRef.current?.click()}
          className={button}
        >
          {variant === "field" && !photo ? t("check.field.add") : t("check.photo.gallery")}
        </button>
        {photo && (variant === "field" || bad) && (
          <button type="button" onClick={onClear} className="min-h-11 px-3 font-medium text-brand underline">
            {t("check.photo.remove")}
          </button>
        )}
      </div>
    </div>
  );
}
