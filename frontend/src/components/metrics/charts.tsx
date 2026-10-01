"use client";

import { Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

/**
 * Recharts wrappers. Recharts writes colours into SVG attributes, where CSS variables do not work, so the design-system
 * colours are repeated here as hex (they are the same values as in globals.css). Every chart sits next to a table with
 * the exact numbers, and is described by a figcaption, so none of the information is colour-only or chart-only.
 */
export const CHART = {
  brand: "#1f5b3a",
  info: "#1d4f8c",
  soil: "#8a5a33",
  warning: "#8a6212",
  danger: "#a3261b",
  grid: "#d9d6c8",
  text: "#4a5a4f",
} as const;

const tick = { fill: CHART.text, fontSize: 12 };

export type HBarDatum = { name: string; value: number; color?: string };

/** One horizontal bar per row, with its value written at the end of the bar. */
export function HBar({ data, caption, format, color = CHART.brand, max }: { data: HBarDatum[]; caption: string; format: (v: number) => string; color?: string; max?: number }) {
  return (
    <figure aria-label={caption} className="w-full">
      <figcaption className="sr-only">{caption}</figcaption>
      <ResponsiveContainer width="100%" height={Math.max(60, data.length * 38 + 16)}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 56, bottom: 4, left: 4 }} barCategoryGap={6}>
          <CartesianGrid horizontal={false} stroke={CHART.grid} />
          <XAxis type="number" hide domain={[0, max ?? "auto"]} />
          <YAxis type="category" dataKey="name" width={150} tick={tick} tickLine={false} axisLine={false} interval={0} />
          <Bar dataKey="value" isAnimationActive={false} radius={[0, 3, 3, 0]}>
            {data.map((d) => (
              <Cell key={d.name} fill={d.color ?? color} />
            ))}
            <LabelList dataKey="value" position="right" formatter={(v: unknown) => format(Number(v))} fill={CHART.text} fontSize={12} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </figure>
  );
}

export type Series = { key: string; label: string; color: string };

/** Grouped vertical bars: one group per category, one bar per series, with a legend and a tooltip. */
export function GroupBars({ data, series, caption, format }: { data: Record<string, number | string>[]; series: Series[]; caption: string; format: (v: number) => string }) {
  return (
    <figure aria-label={caption} className="w-full">
      <figcaption className="sr-only">{caption}</figcaption>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
          <CartesianGrid vertical={false} stroke={CHART.grid} />
          <XAxis dataKey="name" tick={tick} tickLine={false} interval={0} />
          <YAxis tick={tick} tickLine={false} axisLine={false} tickFormatter={(v: number) => format(v)} width={64} />
          <Tooltip formatter={(v: unknown) => format(Number(v))} />
          <Legend />
          {series.map((s) => (
            <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} isAnimationActive={false} radius={[3, 3, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </figure>
  );
}
