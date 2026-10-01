import { getTranslator } from "@/i18n/server";
import type { SessionInfo } from "@/lib/auth/session";

/** Stand-in for a screen that is not built yet. Shows only the real session, no sample data. */
export async function SessionPlaceholder({ session }: { session: SessionInfo }) {
  const { t } = await getTranslator();
  return (
    <section>
      <h1 className="text-title font-bold">{t(`placeholder.${session.role}.title`)}</h1>
      <p className="mt-2 text-ink-muted">{t("placeholder.notBuilt")}</p>
      <dl className="mt-6 space-y-1 text-sm text-ink-muted">
        {session.email && <dd>{t("placeholder.signedInAs", { email: session.email })}</dd>}
        <dd>{t("placeholder.role", { role: t(`role.${session.role}`) })}</dd>
      </dl>
    </section>
  );
}
