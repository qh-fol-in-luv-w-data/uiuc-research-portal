import { Reveal } from "@/components/motion/Reveal";
import { SectionHeading } from "@/components/SectionHeading";
import { fmt, monthLabel } from "@/lib/format";
import type { StatsData } from "@/lib/types";

import { MonthlyChart } from "./MonthlyChart";

const TYPE_LABEL: Record<string, string> = {
  article: "Article", preprint: "Preprint", "conference-paper": "Conference paper", "book-chapter": "Book chapter", review: "Review",
};
const TYPE_COLOR = ["bg-navy", "bg-navy-3", "bg-accent", "bg-hero-muted", "bg-line"];

export function Output({ monthly, types, venues, oaShare }: {
  monthly: StatsData["monthly"]; types: StatsData["types"]; venues: StatsData["top_venues"]; oaShare: number;
}) {
  const today = new Date().toISOString().slice(0, 7);
  const series = monthly.filter((m) => m.month <= today); // drop future-dated issue months
  const partial = series.at(-1)?.month === today ? today : null;
  const total = types.reduce((a, t) => a + t.count, 0);
  return (
    <section id="output" aria-labelledby="output-title" className="cv-auto flex scroll-mt-24 flex-col gap-6">
      <SectionHeading id="output" title="Scholarly output"
        intro="About a thousand works a month. January peaks include works OpenAlex dates only by year, which it files under 1 January." />
      <Reveal className="overflow-x-auto rounded-2xl border border-line bg-surface p-5">
        <MonthlyChart data={series} partialMonth={partial} />
        {partial && <p className="mt-2 text-xs text-muted">{monthLabel(partial)} is still in progress.</p>}
      </Reveal>
      <div className="grid gap-4 md:grid-cols-3">
        <Reveal className="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-5 md:col-span-2">
          <h3 className="text-lg font-semibold">By publication type</h3>
          <div role="img" aria-label={types.map((t) => `${TYPE_LABEL[t.type] ?? t.type} ${Math.round((t.count / total) * 100)}%`).join(", ")}
               className="flex h-4 gap-0.5 overflow-hidden rounded-md">
            {types.map((t, i) => <div key={t.type} className={TYPE_COLOR[i] ?? "bg-line"} style={{ flex: `${t.count} 1 0` }} />)}
          </div>
          <ul className="grid gap-2 sm:grid-cols-2">
            {types.map((t, i) => (
              <li key={t.type} className="grid grid-cols-[12px_minmax(0,1fr)_auto_auto] items-center gap-2.5 text-sm">
                <span aria-hidden="true" className={`h-3 w-3 rounded-sm ${TYPE_COLOR[i] ?? "bg-line"}`} />
                <span>{TYPE_LABEL[t.type] ?? t.type}</span>
                <span className="tabular font-mono text-muted">{fmt(t.count)}</span>
                <span className="tabular w-10 text-right font-mono">{Math.round((t.count / total) * 100)}%</span>
              </li>
            ))}
          </ul>
          <p className="border-t border-line pt-3 text-sm text-muted">
            <strong className="text-ink">{(oaShare * 100).toFixed(1)}%</strong> are open access: free to read at publication.
          </p>
        </Reveal>
        <Reveal delay={0.08} className="flex flex-col gap-2 rounded-2xl border border-line bg-surface p-5">
          <h3 className="text-lg font-semibold">Top venues</h3>
          <ol>
            {venues.slice(0, 7).map((v) => (
              <li key={v.name} className="flex justify-between gap-3 border-t border-line py-2 text-sm first:border-t-0">
                <span className="min-w-0 truncate" title={v.name}>{v.name.replace(/ \(.*\)$/, "")}</span>
                <span className="tabular font-mono text-muted">{fmt(v.count)}</span>
              </li>
            ))}
          </ol>
        </Reveal>
      </div>
    </section>
  );
}
