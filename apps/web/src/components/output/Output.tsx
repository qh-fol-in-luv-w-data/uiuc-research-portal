import { Reveal } from "@/components/motion/Reveal";
import { SectionHeading } from "@/components/SectionHeading";
import { getI18n } from "@/i18n/server";
import type { StatsData } from "@/lib/types";

import { MonthlyChart } from "./MonthlyChart";

const TYPE_COLOR = ["bg-navy", "bg-navy-3", "bg-accent", "bg-hero-muted", "bg-line"];

export async function Output({ monthly, types, venues, oaShare }: {
  monthly: StatsData["monthly"]; types: StatsData["types"]; venues: StatsData["top_venues"]; oaShare: number;
}) {
  const { t, f } = await getI18n();
  const today = new Date().toISOString().slice(0, 7);
  const series = monthly.filter((m) => m.month <= today); // drop future-dated issue months
  const partial = series.at(-1)?.month === today ? today : null;
  const total = types.reduce((a, ty) => a + ty.count, 0);
  return (
    <section id="output" aria-labelledby="output-title" className="flex scroll-mt-24 flex-col gap-6">
      <SectionHeading id="output" title={t.sections.output[0]} intro={t.sections.output[1]} />
      <Reveal className="overflow-x-auto rounded-2xl border border-line bg-surface p-5">
        <MonthlyChart data={series} partialMonth={partial} />
        {partial && <p className="mt-2 text-xs text-muted">{t.output.inProgress(f.monthLabel(partial))}</p>}
      </Reveal>
      <div className="grid gap-4 md:grid-cols-3">
        <Reveal className="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-5 md:col-span-2">
          <h3 className="text-lg font-semibold">{t.output.byType}</h3>
          <div role="img" aria-label={types.map((ty) => `${f.type(ty.type)} ${Math.round((ty.count / total) * 100)}%`).join(", ")}
               className="flex h-4 gap-0.5 overflow-hidden rounded-md">
            {types.map((ty, i) => <div key={ty.type} className={TYPE_COLOR[i] ?? "bg-line"} style={{ flex: `${ty.count} 1 0` }} />)}
          </div>
          <ul className="grid gap-2 sm:grid-cols-2">
            {types.map((ty, i) => (
              <li key={ty.type} className="grid grid-cols-[12px_minmax(0,1fr)_auto_auto] items-center gap-2.5 text-sm">
                <span aria-hidden="true" className={`h-3 w-3 rounded-sm ${TYPE_COLOR[i] ?? "bg-line"}`} />
                <span>{f.type(ty.type)}</span>
                <span className="tabular font-mono text-muted">{f.fmt(ty.count)}</span>
                <span className="tabular w-10 text-right font-mono">{Math.round((ty.count / total) * 100)}%</span>
              </li>
            ))}
          </ul>
          <p className="border-t border-line pt-3 text-sm text-muted">
            <strong className="text-ink">{t.output.oa(f.pct(oaShare))[0]}</strong>{t.output.oa(f.pct(oaShare))[1]}
          </p>
        </Reveal>
        <Reveal delay={0.08} className="flex flex-col gap-2 rounded-2xl border border-line bg-surface p-5">
          <h3 className="text-lg font-semibold">{t.output.venues}</h3>
          <ol>
            {venues.slice(0, 7).map((v) => (
              <li key={v.name} className="flex justify-between gap-3 border-t border-line py-2 text-sm first:border-t-0">
                <span className="min-w-0 truncate" title={v.name}>{v.name.replace(/ \(.*\)$/, "")}</span>
                <span className="tabular font-mono text-muted">{f.fmt(v.count)}</span>
              </li>
            ))}
          </ol>
        </Reveal>
      </div>
    </section>
  );
}
