import type { Metadata } from "next";
import { ExpertWorkspace } from "@/components/expert/ExpertWorkspace";
import { requireRole } from "@/lib/auth/server";
import { isStatusFilter } from "@/lib/expert";

export const metadata: Metadata = { title: "Review queue" };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

export default async function ExpertHomePage({ searchParams }: PageProps<"/expert">) {
  await requireRole("expert");
  const q = await searchParams;
  const status = one(q.status);
  const caseId = one(q.case);
  return <ExpertWorkspace status={isStatusFilter(status) ? status : "pending_review"} caseId={caseId && UUID.test(caseId) ? caseId : null} />;
}
