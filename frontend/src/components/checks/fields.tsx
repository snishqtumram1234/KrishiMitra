"use client";

import type { ReactNode } from "react";

export const inputClass = (invalid: boolean) =>
  `mt-1 block min-h-12 w-full rounded-control border bg-field px-3 py-2 text-ink placeholder:text-placeholder disabled:bg-sunken disabled:text-disabled ${
    invalid ? "border-danger-solid" : "border-control-border"
  }`;

export function Section({ title, badge, children }: { title: string; badge?: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="flex items-baseline gap-2 text-lg font-bold">
        {title}
        {badge && <span className="rounded-control bg-sunken px-2 text-sm font-medium text-ink-muted">{badge}</span>}
      </h2>
      {children}
    </section>
  );
}

export function Field({
  id,
  label,
  hint,
  error,
  counter,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string | null;
  counter?: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="font-medium">
        {label}
      </label>
      {hint && (
        <p id={`${id}-hint`} className="text-sm text-ink-muted">
          {hint}
        </p>
      )}
      {children}
      <div className="mt-1 flex justify-between gap-2 text-sm">
        <p id={`${id}-error`} className="text-danger-fg">
          {error ?? ""}
        </p>
        {counter && <p className="shrink-0 text-ink-muted">{counter}</p>}
      </div>
    </div>
  );
}

export const describedBy = (id: string, hasHint: boolean, hasError: boolean) =>
  [hasHint ? `${id}-hint` : null, hasError ? `${id}-error` : null].filter(Boolean).join(" ") || undefined;

export function ErrorSummary({
  title,
  items,
  summaryRef,
}: {
  title: string;
  items: { targetId: string; text: string }[];
  summaryRef: React.RefObject<HTMLDivElement | null>;
}) {
  if (items.length === 0) return null;
  return (
    <div ref={summaryRef} tabIndex={-1} role="alert" className="rounded-card border border-danger-solid bg-danger-bg p-4 text-danger-fg">
      <p className="font-bold">{title}</p>
      <ul className="mt-2 list-disc ps-5">
        {items.map((item) => (
          <li key={item.targetId}>
            <a
              href={`#${item.targetId}`}
              className="underline"
              onClick={(e) => {
                e.preventDefault();
                document.getElementById(item.targetId)?.focus();
              }}
            >
              {item.text}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
