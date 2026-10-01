import { SessionPlaceholder } from "@/components/shell/SessionPlaceholder";
import { requireRole } from "@/lib/auth/server";

export default async function DashboardPage() {
  return <SessionPlaceholder session={await requireRole("farmer")} />;
}
