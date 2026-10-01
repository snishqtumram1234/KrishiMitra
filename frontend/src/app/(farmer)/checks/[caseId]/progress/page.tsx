import type { Metadata } from "next";
import { AnalysisProgress } from "@/components/result/AnalysisProgress";
import { getTranslator } from "@/i18n/server";

export const metadata: Metadata = { title: "How we checked" };

export default async function ProgressPage({ params }: PageProps<"/checks/[caseId]/progress">) {
  const { t } = await getTranslator();
  const { caseId } = await params;
  return (
    <div className="space-y-4">
      <h1 className="text-title font-bold">{t("progress.title")}</h1>
      <AnalysisProgress caseId={caseId} />
    </div>
  );
}
