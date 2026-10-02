import type { Metadata } from "next";
import { ResultView } from "@/components/result/ResultView";
import { getTranslator } from "@/i18n/server";

export const metadata: Metadata = { title: "Your result" };

export default async function CheckResultPage({ params }: PageProps<"/checks/[caseId]">) {
  const { t } = await getTranslator();
  const { caseId } = await params;
  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <h1 className="text-title font-bold">{t("result.title")}</h1>
      <ResultView caseId={caseId} />
    </div>
  );
}
