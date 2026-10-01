import { getTranslator } from "@/i18n/server";

/** A plain form POST, so sign-out works even before any JavaScript has loaded. */
export async function SignOutButton({ label }: { label?: string }) {
  const { t } = await getTranslator();
  return (
    <form action="/auth/signout" method="post">
      <button type="submit" className="min-h-11 rounded-control px-3 text-sm font-medium text-brand underline">
        {label ?? t("common.signOut")}
      </button>
    </form>
  );
}
