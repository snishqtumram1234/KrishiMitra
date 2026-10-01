"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/i18n/client";
import { HOME } from "@/lib/auth/routing";
import { roleFromClaims } from "@/lib/auth/roles";
import { createBrowserSupabase } from "@/lib/supabase/browser";

/**
 * "Try again" on the 403 page. The role lives in the access token, so a freshly granted role only shows up after the
 * token is refreshed. This refreshes it and goes to the expert queue if the account now qualifies.
 */
export function RetryAccess() {
  const { t } = useI18n();
  const router = useRouter();
  const [state, setState] = useState<"idle" | "checking" | "blocked">("idle");

  async function retry() {
    setState("checking");
    try {
      const supabase = createBrowserSupabase();
      await supabase.auth.refreshSession();
      const { data } = await supabase.auth.getClaims();
      if (roleFromClaims(data?.claims) === "expert") {
        router.replace(HOME.expert);
        router.refresh();
        return;
      }
    } catch {
      // fall through to the "still blocked" message
    }
    setState("blocked");
  }

  return (
    <div>
      <button
        type="button"
        onClick={retry}
        disabled={state === "checking"}
        className="min-h-12 rounded-control bg-brand px-4 font-bold text-white disabled:bg-brand-loading"
      >
        {state === "checking" ? t("forbidden.checking") : t("forbidden.tryAgain")}
      </button>
      <p role="status" className="mt-2 text-sm text-danger-fg">
        {state === "blocked" ? t("forbidden.stillBlocked") : ""}
      </p>
    </div>
  );
}
