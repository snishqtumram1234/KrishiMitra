import Link from "next/link";
import type { ReactNode } from "react";
import { LanguageToggle } from "@/components/LanguageToggle";
import { Logo } from "@/components/Logo";
import { SignOutButton } from "@/components/SignOutButton";
import { getTranslator } from "@/i18n/server";

/**
 * The expert workspace. It is only ever rendered by the (expert) layout after the role check passes, never by the
 * 403 page. Metrics joins the nav when that screen is built.
 */
export async function ExpertShell({ children }: { children: ReactNode }) {
  const { t } = await getTranslator();
  return (
    <div className="min-h-dvh">
      <a href="#main" className="sr-only focus:not-sr-only focus:py-2">
        {t("shell.skipToContent")}
      </a>
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
          <div className="flex items-center gap-3">
            <Logo href="/expert" />
            <span className="rounded-control bg-soil-100 px-2 py-0.5 text-sm font-medium text-soil-900">
              {t("shell.badge.expert")}
            </span>
          </div>
          <nav aria-label={t("shell.nav.main")} className="flex items-center gap-4">
            <Link href="/expert" aria-current="page" className="font-medium text-brand underline">
              {t("shell.nav.reviewQueue")}
            </Link>
          </nav>
          <div className="flex items-center gap-1">
            <LanguageToggle />
            <SignOutButton />
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-6xl px-6 py-8">
        {children}
      </main>
    </div>
  );
}
