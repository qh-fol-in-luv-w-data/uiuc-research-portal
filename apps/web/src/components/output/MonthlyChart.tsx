import type { CSSProperties } from "react";

import { getI18n } from "@/i18n/server";
import type { StatsData } from "@/lib/types";

/**
 * Monthly publications as CSS bars (no charting library, no client JS). Bars grow from the baseline
 * as the chart scrolls into view (CSS scroll-driven animation); they are full height by default.
 */
export async function MonthlyChart({ data, partialMonth }: { data: StatsData["monthly"]; partialMonth: string | null }) {
  const { t, f } = await getI18n();
  const { fmt, monthLabel } = f;
  const max = Math.max(...data.map((d) => d.count));
  const step = max > 1500 ? 500 : 250;
  const ticks = Array.from({ length: Math.floor(max / step) }, (_, i) => (i + 1) * step);
  const steady = data.filter((d) => !d.month.endsWith("-01") && d.month !== partialMonth).map((d) => d.count);
  const summary = t.output.summary(monthLabel(data[0].month), monthLabel(data[data.length - 1].month),
    fmt(Math.min(...steady)), fmt(Math.max(...steady)), fmt(max));
  return (
    <div className="min-w-[640px]">
      <div role="img" aria-label={summary} className="relative h-64 pl-12">
        {ticks.map((t) => (
          <div key={t} aria-hidden="true" className="absolute inset-x-0 border-t border-line" style={{ bottom: `${(t / max) * 100}%` }}>
            <span className="tabular absolute -top-2.5 left-0 font-mono text-[11px] text-muted">{fmt(t)}</span>
          </div>
        ))}
        <ol className="relative flex h-full items-end gap-1.5 border-b border-line">
          {data.map((d, i) => {
            const jan = d.month.endsWith("-01");
            const partial = d.month === partialMonth;
            return (
              <li key={d.month} className="group relative flex h-full flex-1 items-end">
                <div
                  className={`grow-bar w-full rounded-t-[3px] transition-colors ${jan ? "bg-navy-3/55" : partial ? "bg-line" : "bg-navy-2"} group-hover:bg-accent`}
                  style={{ height: `${(d.count / max) * 100}%`, "--i": i } as CSSProperties}
                />
                <span role="tooltip" className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded-lg border border-line bg-surface px-3 py-2 text-xs shadow-lg group-hover:block">
                  <strong className="block text-sm">{monthLabel(d.month)}</strong>
                  <span className="tabular font-mono text-muted">{t.output.works(fmt(d.count))}</span>
                  {jan && <span className="block text-muted">{t.output.janNote}</span>}
                  {partial && <span className="block text-muted">{t.output.partial}</span>}
                </span>
              </li>
            );
          })}
        </ol>
      </div>
      <ol aria-hidden="true" className="flex gap-1.5 pl-12 pt-2">
        {data.map((d, i) => (
          <li key={d.month} className="tabular flex-1 text-center font-mono text-[10.5px] text-muted">
            {i % 3 === 0 ? f.axisLabel(d.month) : ""}
          </li>
        ))}
      </ol>
    </div>
  );
}
