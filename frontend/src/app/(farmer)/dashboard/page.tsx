import type { Metadata } from "next";
import { Dashboard } from "@/components/dashboard/Dashboard";
import { requireRole } from "@/lib/auth/server";

export const metadata: Metadata = { title: "Your crop checks" };

export default async function DashboardPage() {
  await requireRole("farmer");
  return <Dashboard />;
}
