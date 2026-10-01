import type { Metadata } from "next";
import Link from "next/link";
import { LanguageToggle } from "@/components/LanguageToggle";
import { Logo } from "@/components/Logo";
import { SignOutButton } from "@/components/SignOutButton";
import { RetryAccess } from "@/components/auth/RetryAccess";
import { getTranslator } from "@/i18n/server";
import { HOME } from "@/lib/auth/routing";
import { getSession } from "@/lib/auth/server";

export const metadata: Metadata = { title: "No access" };

/**
 * Rendered (with a real 403 status) when a signed-in user opens a page their role cannot use. It deliberately uses a
 * neutral header (brand, language, sign out) and never the expert shell, so nothing of the expert workspace is shown.
 */
export default async function ForbiddenPage({ searchParams }: PageProps<"/403">) {
  const { t } = await getTranslator();
  const session = await getSession();
  const area = (await searchParams).area === "expert" ? "expert" : "generic";

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-4">
      <header className="flex items-center justify-between gap-2 py-3">
        <Logo href={session ? HOME[session.role] : "/login"} />
        <div className="flex items-center gap-1">
          <LanguageToggle />
          <SignOutButton />
        </div>
      </header>
      <main id="main" className="flex-1 py-8">
        <p className="eyebrow text-danger-fg">{t("forbidden.code")}</p>
        <h1 className="mt-2 text-title font-bold">{t(`forbidden.${area}.title`)}</h1>
        <p className="mt-3 text-ink-muted">{t(`forbidden.${area}.body`)}</p>

        <div className="mt-6 space-y-4">
          {area === "expert" && <RetryAccess />}
          {session && (
            <Link href={HOME[session.role]} className="inline-flex min-h-11 items-center font-medium text-brand underline">
              {t("forbidden.home")}
            </Link>
          )}
        </div>
        {area === "expert" && <p className="mt-6 text-sm text-ink-muted">{t("forbidden.expert.hint")}</p>}
      </main>
    </div>
  );
}
