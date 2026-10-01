import type { Metadata } from "next";
import Link from "next/link";
import { CropCheckForm } from "@/components/checks/CropCheckForm";
import { QuestionForm } from "@/components/checks/QuestionForm";
import { getTranslator } from "@/i18n/server";

export const metadata: Metadata = { title: "New check" };

/** One screen, two entry points. The tabs are links, so each has its own URL: ?mode=question for the text-only one. */
export default async function NewCheckPage({ searchParams }: PageProps<"/checks/new">) {
  const { t } = await getTranslator();
  const raw = (await searchParams).mode;
  const mode = (Array.isArray(raw) ? raw[0] : raw) === "question" ? "question" : "crop";
  const tabs = [
    { key: "crop", href: "/checks/new", label: t("check.mode.crop") },
    { key: "question", href: "/checks/new?mode=question", label: t("check.mode.question") },
  ] as const;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Link href="/dashboard" aria-label={t("common.back")} className="inline-flex min-h-11 min-w-11 items-center justify-center text-xl">
          <span aria-hidden="true">←</span>
        </Link>
        <h1 className="text-title font-bold">{t("check.title")}</h1>
      </div>

      <nav aria-label={t("check.mode.label")} className="grid grid-cols-2 rounded-control bg-sunken p-1">
        {tabs.map((tab) => (
          <Link
            key={tab.key}
            href={tab.href}
            aria-current={tab.key === mode ? "page" : undefined}
            className={`flex min-h-11 items-center justify-center rounded-control text-center font-medium ${
              tab.key === mode ? "bg-surface text-ink shadow-segment" : "text-ink-muted"
            }`}
          >
            {tab.label}
          </Link>
        ))}
      </nav>

      {mode === "crop" ? <CropCheckForm key="crop" /> : <QuestionForm key="question" />}
    </div>
  );
}
