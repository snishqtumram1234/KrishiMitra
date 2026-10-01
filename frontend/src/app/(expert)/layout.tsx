import type { ReactNode } from "react";
import { ExpertShell } from "@/components/shell/ExpertShell";
import { requireRole } from "@/lib/auth/server";

export default async function ExpertLayout({ children }: { children: ReactNode }) {
  await requireRole("expert");
  return <ExpertShell>{children}</ExpertShell>;
}
