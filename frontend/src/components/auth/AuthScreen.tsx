import Link from "next/link";
import { LanguageToggle } from "@/components/LanguageToggle";
import { Logo } from "@/components/Logo";
import { getTranslator } from "@/i18n/server";
import { isAuthErrorKind } from "@/lib/auth/errors";
import { isSupabaseConfigured } from "@/lib/env";
import { AuthForm } from "./AuthForm";

type Search = { next?: string | string[]; error?: string | string[]; reason?: string | string[] };
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

/** Shared by /login and /signup. The tabs are real links, so each mode has its own URL. */
export async function AuthScreen({ mode, search }: { mode: "signIn" | "signUp"; search: Search }) {
  const { t } = await getTranslator();
  const next = one(search.next) ?? null;
  const error = one(search.error);
  const query = next ? `?next=${encodeURIComponent(next)}` : "";
  const tabs = [
    { key: "signIn", href: `/login${query}`, label: t("auth.tab.signIn") },
    { key: "signUp", href: `/signup${query}`, label: t("auth.tab.signUp") },
  ] as const;

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-5xl flex-col px-4 py-4 sm:px-8 sm:py-6">
      <header className="flex items-center justify-between">
        <Logo />
        <LanguageToggle />
      </header>

      <main id="main" className="flex-1 py-8 lg:grid lg:grid-cols-2 lg:items-center lg:gap-16 lg:py-12">
        <div>
          <h1 className="text-hero font-bold text-ink lg:text-5xl lg:leading-[1.1]">
            {mode === "signIn" ? t("auth.hero.title") : t("auth.signUp.title")}
          </h1>
          <p className="mt-2 text-ink-muted lg:mt-4 lg:text-lg">
            {mode === "signIn" ? t("auth.hero.subtitle") : t("auth.signUp.subtitle")}
          </p>
          <p className="mt-6 hidden text-sm text-ink-muted lg:block">
            {one(search.reason) === "session_expired" ? t("auth.footer.sessionExpired") : t("auth.footer.disclaimer")}
          </p>
        </div>

        <div className="mt-6 lg:mt-0 lg:rounded-card lg:border lg:border-line lg:bg-surface lg:p-8">
          <nav aria-label={t("auth.tabs.label")} className="grid grid-cols-2 rounded-control bg-sunken p-1">
            {tabs.map((tab) => (
              <Link
                key={tab.key}
                href={tab.href}
                aria-current={tab.key === mode ? "page" : undefined}
                className={`flex min-h-11 items-center justify-center rounded-control font-medium ${
                  tab.key === mode ? "bg-surface text-ink shadow-segment" : "text-ink-muted"
                }`}
              >
                {tab.label}
              </Link>
            ))}
          </nav>

          <div className="mt-6">
            <AuthForm
              key={mode}
              mode={mode}
              configured={isSupabaseConfigured()}
              next={next}
              initialError={isAuthErrorKind(error) ? error : null}
            />
          </div>
        </div>
      </main>

      <footer className="pb-4 text-sm text-ink-muted lg:hidden">
        <p>{one(search.reason) === "session_expired" ? t("auth.footer.sessionExpired") : t("auth.footer.disclaimer")}</p>
      </footer>
    </div>
  );
}
