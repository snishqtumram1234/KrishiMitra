import type { ReactNode } from "react";
import { FarmerShell } from "@/components/shell/FarmerShell";
import { requireRole } from "@/lib/auth/server";

export default async function FarmerLayout({ children }: { children: ReactNode }) {
  await requireRole("farmer");
  return <FarmerShell>{children}</FarmerShell>;
}
