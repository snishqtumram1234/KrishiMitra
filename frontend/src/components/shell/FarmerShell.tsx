import Link from "next/link";
import type { ReactNode } from "react";
import { LanguageToggle } from "@/components/LanguageToggle";
import { Logo } from "@/components/Logo";
import { SignOutButton } from "@/components/SignOutButton";
import { getTranslator } from "@/i18n/server";

/** The farmer's workspace: a full-width top bar and a centred content area that uses the room a laptop screen has. */
export async function FarmerShell({ children }: { children: ReactNode }) {
  const { t } = await getTranslator();
  return (
    <div className="min-h-dvh">
      <a href="#main" className="sr-only focus:not-sr-only focus:py-2">
        {t("shell.skipToContent")}
      </a>
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-6">
            <Logo href="/dashboard" />
            <nav aria-label={t("shell.nav.main")} className="hidden items-center gap-4 sm:flex">
              <Link href="/dashboard" className="inline-flex min-h-11 items-center font-medium text-ink-muted hover:text-brand">
                {t("dashboard.title")}
              </Link>
              <Link href="/checks/new" className="inline-flex min-h-11 items-center font-medium text-ink-muted hover:text-brand">
                {t("dashboard.newCheck")}
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-1">
            <LanguageToggle />
            <SignOutButton />
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        {children}
      </main>
    </div>
  );
}
