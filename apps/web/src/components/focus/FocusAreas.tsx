import { Suspense } from "react";

import { Reveal } from "@/components/motion/Reveal";
import { SectionHeading } from "@/components/SectionHeading";
import { fmt } from "@/lib/format";
import type { StatsData } from "@/lib/types";

import { FieldTiles } from "./FieldTiles";

export function FocusAreas({ fields, rising, topFaculty }: {
  fields: StatsData["fields"]; rising: StatsData["rising_topics"]; topFaculty: StatsData["top_faculty"];
}) {
  const max = topFaculty[0]?.count ?? 1;
  return (
    <section id="focus" aria-labelledby="focus-title" className="flex scroll-mt-24 flex-col gap-6 pt-16">
      <SectionHeading id="focus" title="Research focus areas"
        intro="Publications grouped by the OpenAlex field of their primary topic. Tile size follows publication count." />
      <Suspense fallback={<div className="h-72 animate-pulse rounded-xl bg-surface" />}>
        <FieldTiles fields={fields} />
      </Suspense>
      <div className="grid gap-4 md:grid-cols-2">
        <Reveal className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-5">
          <h3 className="text-lg font-semibold">Rising topics</h3>
          <p className="text-sm text-muted">Last 12 months against the 12 before, topics with at least 40 recent works.</p>
          <ol className="flex flex-col">
            {rising.slice(0, 6).map((r) => (
              <li key={r.id} className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-0.5 border-t border-line py-2.5 first:border-t-0">
                <span className="font-medium">{r.name}</span>
                <span className="tabular font-mono text-sm font-medium text-accent-ink">×{r.growth.toFixed(1)}</span>
                <span className="text-xs text-muted">{r.field}</span>
                <span className="tabular font-mono text-xs text-muted">{r.prior} → {r.recent}</span>
              </li>
            ))}
          </ol>
        </Reveal>
        <Reveal delay={0.08} className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-5">
          <h3 className="text-lg font-semibold">Most published faculty</h3>
          <p className="text-sm text-muted">Works by faculty matched to an OpenAlex author profile.</p>
          <ol className="flex flex-col gap-3">
            {topFaculty.slice(0, 6).map((t) => (
              <li key={t.id} className="flex flex-col gap-1">
                <div className="flex justify-between text-sm">
                  <span className="font-medium">{t.name}</span>
                  <span className="tabular font-mono text-muted">{fmt(t.count)}</span>
                </div>
                <div className="h-2 rounded bg-surface-2">
                  <div className="h-2 origin-left rounded bg-navy-2" style={{ width: `${(t.count / max) * 100}%` }} />
                </div>
              </li>
            ))}
          </ol>
        </Reveal>
      </div>
    </section>
  );
}
