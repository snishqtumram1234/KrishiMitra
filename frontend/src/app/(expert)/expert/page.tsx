import { SessionPlaceholder } from "@/components/shell/SessionPlaceholder";
import { requireRole } from "@/lib/auth/server";

export default async function ExpertHomePage() {
  return <SessionPlaceholder session={await requireRole("expert")} />;
}
