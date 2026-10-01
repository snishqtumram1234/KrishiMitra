import type { Metadata } from "next";
import { MetricsDashboard } from "@/components/metrics/MetricsDashboard";
import { requireRole } from "@/lib/auth/server";
import { parseWindow } from "@/lib/metrics";

export const metadata: Metadata = { title: "Metrics" };

export default async function MetricsPage({ searchParams }: PageProps<"/metrics">) {
  await requireRole("expert");
  const raw = (await searchParams).days;
  return <MetricsDashboard days={parseWindow(Array.isArray(raw) ? raw[0] : raw)} />;
}
