import { draftBadgeFlag } from "@/lib/env";
import type { Locale } from "@/i18n/locales";
import { DRAFT_BADGE_TEXT, shouldShowDraftBadge } from "@/i18n/review";

/**
 * Shown on every page while the UI is Marathi and any Marathi string is unreviewed. Deliberately English: it is for
 * the team and reviewers, not farmers, and turns off with NEXT_PUBLIC_SHOW_DRAFT_BADGES=false.
 */
export function DraftBadge({ locale }: { locale: Locale }) {
  if (!shouldShowDraftBadge(locale, draftBadgeFlag())) return null;
  return (
    <div lang="en" role="note" className="bg-warning-bg px-4 py-1 text-center text-sm font-medium text-warning-fg">
      {DRAFT_BADGE_TEXT}
    </div>
  );
}
