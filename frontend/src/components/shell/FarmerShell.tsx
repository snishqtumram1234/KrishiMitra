import type { ReactNode } from "react";
import { LanguageToggle } from "@/components/LanguageToggle";
import { Logo } from "@/components/Logo";
import { SignOutButton } from "@/components/SignOutButton";
import { getTranslator } from "@/i18n/server";

export async function FarmerShell({ children }: { children: ReactNode }) {
  const { t } = await getTranslator();
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-4">
      <a href="#main" className="sr-only focus:not-sr-only focus:py-2">
        {t("shell.skipToContent")}
      </a>
      <header className="flex items-center justify-between gap-2 py-3">
        <Logo href="/dashboard" />
        <div className="flex items-center gap-1">
          <LanguageToggle />
          <SignOutButton />
        </div>
      </header>
      <main id="main" className="flex-1 py-4">
        {children}
      </main>
    </div>
  );
}
