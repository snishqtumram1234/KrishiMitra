"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useI18n } from "@/i18n/client";

/** The expert workspace's two tabs, with the current one marked. Rendered only inside the expert shell. */
export function ExpertNav() {
  const { t } = useI18n();
  const path = usePathname();
  const items = [
    { href: "/expert", label: t("shell.nav.reviewQueue"), active: path === "/expert" || path.startsWith("/expert/") },
    { href: "/metrics", label: t("shell.nav.metrics"), active: path === "/metrics" || path.startsWith("/metrics/") },
  ];
  return (
    <nav aria-label={t("shell.nav.main")} className="flex items-center gap-4">
      {items.map((i) => (
        <Link key={i.href} href={i.href} aria-current={i.active ? "page" : undefined} className={`inline-flex min-h-11 items-center font-medium ${i.active ? "text-brand underline" : "text-ink-muted"}`}>
          {i.label}
        </Link>
      ))}
    </nav>
  );
}
