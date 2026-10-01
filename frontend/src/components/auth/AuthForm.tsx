"use client";

import { useId, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { authErrorKind, type AuthErrorKind } from "@/lib/auth/errors";
import { HOME, safeNext } from "@/lib/auth/routing";
import { roleFromClaims } from "@/lib/auth/roles";
import { MIN_PASSWORD_LENGTH } from "@/lib/env";
import { createBrowserSupabase } from "@/lib/supabase/browser";

type Mode = "signIn" | "signUp";
type FieldErrors = { email?: MessageKey; password?: MessageKey };

const EMAIL_SHAPE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validate(mode: Mode, email: string, password: string): FieldErrors {
  const errors: FieldErrors = {};
  if (!email.trim()) errors.email = "auth.validation.emailRequired";
  else if (!EMAIL_SHAPE.test(email.trim())) errors.email = "auth.validation.emailInvalid";
  if (!password) errors.password = "auth.validation.passwordRequired";
  else if (mode === "signUp" && password.length < MIN_PASSWORD_LENGTH) errors.password = "auth.validation.passwordShort";
  return errors;
}

export function AuthForm({
  mode,
  configured,
  next,
  initialError,
}: {
  mode: Mode;
  configured: boolean;
  next: string | null;
  initialError: AuthErrorKind | null;
}) {
  const { t } = useI18n();
  const router = useRouter();
  const id = useId();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<AuthErrorKind | null>(configured ? initialError : "notConfigured");
  const [submitting, setSubmitting] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || !configured) return;
    const errors = validate(mode, email, password);
    setFieldErrors(errors);
    if (errors.email || errors.password) return;

    setError(null);
    setSubmitting(true);
    try {
      const supabase = createBrowserSupabase();
      const address = email.trim();
      if (mode === "signIn") {
        const { error: failure } = await supabase.auth.signInWithPassword({ email: address, password });
        if (failure) return setError(authErrorKind(failure));
      } else {
        const callback = new URL("/auth/callback", window.location.origin);
        if (next) callback.searchParams.set("next", next);
        const { data, error: failure } = await supabase.auth.signUp({
          email: address,
          password,
          options: { emailRedirectTo: callback.toString() },
        });
        if (failure) return setError(authErrorKind(failure));
        if (!data.session) return setSentTo(address); // email confirmation is on: wait for the link
      }
      const { data: claims } = await supabase.auth.getClaims();
      const role = roleFromClaims(claims?.claims);
      router.replace(safeNext(next, role) ?? HOME[role]);
      router.refresh();
    } catch (failure) {
      setError(authErrorKind(failure) === "generic" ? "network" : authErrorKind(failure));
    } finally {
      setSubmitting(false);
    }
  }

  if (sentTo) {
    return (
      <div role="status" className="rounded-card border border-line bg-surface p-5">
        <h2 className="text-xl font-bold">{t("auth.checkEmail.title")}</h2>
        <p className="mt-2 text-ink-muted">{t("auth.checkEmail.body", { email: sentTo })}</p>
        <Link href="/login" className="mt-4 inline-flex min-h-11 items-center font-medium text-brand underline">
          {t("auth.checkEmail.back")}
        </Link>
      </div>
    );
  }

  const disabled = submitting || !configured;
  const emailId = `${id}-email`;
  const passwordId = `${id}-password`;
  const inputClass = (invalid: boolean) =>
    `mt-1 block min-h-12 w-full rounded-control border bg-field px-3 text-ink placeholder:text-placeholder disabled:bg-sunken disabled:text-disabled ${
      invalid ? "border-danger-solid" : "border-control-border"
    }`;

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4">
      {error && (
        <div role="alert" className="rounded-card border border-danger-solid bg-danger-bg p-4 text-danger-fg">
          <p className="font-bold">{t(`auth.error.${error}.title`)}</p>
          <p className="mt-1">{t(`auth.error.${error}.body`, { min: MIN_PASSWORD_LENGTH })}</p>
        </div>
      )}

      <div>
        <label htmlFor={emailId} className="font-medium">
          {t("auth.field.email")}
        </label>
        <input
          id={emailId}
          type="email"
          autoComplete="email"
          inputMode="email"
          value={email}
          disabled={disabled}
          placeholder={t("auth.field.emailPlaceholder")}
          aria-invalid={fieldErrors.email ? true : undefined}
          aria-describedby={fieldErrors.email ? `${emailId}-error` : undefined}
          onChange={(e) => setEmail(e.target.value)}
          className={inputClass(!!fieldErrors.email)}
        />
        {fieldErrors.email && (
          <p id={`${emailId}-error`} className="mt-1 text-sm text-danger-fg">
            {t(fieldErrors.email)}
          </p>
        )}
      </div>

      <div>
        <label htmlFor={passwordId} className="font-medium">
          {t("auth.field.password")}
        </label>
        <input
          id={passwordId}
          type="password"
          autoComplete={mode === "signIn" ? "current-password" : "new-password"}
          value={password}
          disabled={disabled}
          placeholder={mode === "signUp" ? t("auth.field.passwordPlaceholder", { min: MIN_PASSWORD_LENGTH }) : undefined}
          aria-invalid={fieldErrors.password ? true : undefined}
          aria-describedby={fieldErrors.password ? `${passwordId}-error` : undefined}
          onChange={(e) => setPassword(e.target.value)}
          className={inputClass(!!fieldErrors.password)}
        />
        {fieldErrors.password && (
          <p id={`${passwordId}-error`} className="mt-1 text-sm text-danger-fg">
            {t(fieldErrors.password, { min: MIN_PASSWORD_LENGTH })}
          </p>
        )}
      </div>

      <button
        type="submit"
        disabled={disabled}
        aria-busy={submitting}
        className="min-h-12 w-full rounded-control bg-brand px-4 font-bold text-white disabled:bg-brand-loading"
      >
        {submitting ? t(`auth.submitting.${mode}`) : t(`auth.submit.${mode}`)}
      </button>

      {mode === "signUp" && <p className="text-sm text-ink-muted">{t("auth.signUp.note")}</p>}
    </form>
  );
}
