"use client";

import { useInView, useReducedMotion } from "motion/react";
import { useRef } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { fmt, monthLabel } from "@/lib/format";
import type { StatsData } from "@/lib/types";

export function MonthlyChart({ data, partialMonth }: { data: StatsData["monthly"]; partialMonth: string | null }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "0px 0px -15% 0px" });
  const reduce = useReducedMotion();
  const counts = data.map((d) => d.count);
  const steady = data.filter((d) => !d.month.endsWith("-01") && d.month !== partialMonth).map((d) => d.count);
  const summary = `Monthly publications from ${monthLabel(data[0].month)} to ${monthLabel(data[data.length - 1].month)}: `
    + `usually ${fmt(Math.min(...steady))} to ${fmt(Math.max(...steady))} a month, peaking at ${fmt(Math.max(...counts))} in January.`;
  return (
    <div ref={ref} role="img" aria-label={summary} className="h-72 w-full min-w-[640px]">
      {(inView || reduce) && (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} className="chart-grid" />
            <XAxis dataKey="month" tickLine={false} axisLine={false} interval={2} className="chart-axis"
                   tickFormatter={(m: string) => monthLabel(m).replace(" 20", " ’")} />
            <YAxis tickLine={false} axisLine={false} width={44} className="chart-axis" tickFormatter={(v: number) => fmt(v)} />
            <Tooltip cursor={{ className: "chart-cursor" }} content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload as { month: string; count: number };
              return (
                <div className="rounded-lg border border-line bg-surface px-3 py-2 text-sm shadow-lg">
                  <div className="font-medium">{monthLabel(d.month)}</div>
                  <div className="tabular font-mono text-muted">{fmt(d.count)} works</div>
                  {d.month.endsWith("-01") && <div className="text-xs text-muted">Includes works dated only by year</div>}
                  {d.month === partialMonth && <div className="text-xs text-muted">Partial month</div>}
                </div>
              );
            }} />
            <Bar dataKey="count" radius={[3, 3, 0, 0]} isAnimationActive={!reduce} animationDuration={900} animationEasing="ease-out">
              {data.map((d) => (
                <Cell key={d.month} className={d.month.endsWith("-01") ? "bar-jan" : d.month === partialMonth ? "bar-partial" : "bar-main"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
