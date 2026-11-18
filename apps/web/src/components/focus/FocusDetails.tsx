"use client";

import { ArrowDown } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { openFaculty } from "@/lib/facultyEvents";
import { fmt } from "@/lib/format";
import type { StatsData } from "@/lib/types";
import { useField } from "@/lib/useField";

type Props = {
  fields: StatsData["fields"];
  rising: StatsData["rising_topics"];
  topFaculty: StatsData["top_faculty"];
  byField: StatsData["by_field"];
};

function Card({ title, note, children }: { title: string; note: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-5">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-sm text-muted">{note}</p>
      {children}
    </div>
  );
}

function RisingList({ items }: { items: StatsData["rising_topics"] }) {
  if (!items.length) return <p className="text-sm text-muted">No topic in this field has grown on enough recent works.</p>;
  return (
    <ol className="flex flex-col">
      {items.map((r) => (
        <li key={r.id} className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-0.5 border-t border-line py-2.5 first:border-t-0">
          <span className="font-medium">{r.name}</span>
          <span className="tabular font-mono text-sm font-medium text-accent-ink">×{r.growth.toFixed(1)}</span>
          <span className="text-xs text-muted">{r.field}</span>
          <span className="tabular font-mono text-xs text-muted">{r.prior} → {r.recent}</span>
        </li>
      ))}
    </ol>
  );
}

function FacultyBars({ items }: { items: StatsData["top_faculty"] }) {
  const max = items[0]?.count ?? 1;
  if (!items.length) return <p className="text-sm text-muted">No linked faculty publish in this field yet.</p>;
  return (
    <ol className="flex flex-col gap-3">
      {items.map((t) => (
        <li key={t.id} className="flex flex-col gap-1">
          <div className="flex justify-between text-sm">
            <button type="button" onClick={() => openFaculty(t.id)} className="font-medium hover:text-accent-ink hover:underline">{t.name}</button>
            <span className="tabular font-mono text-muted">{fmt(t.count)}</span>
          </div>
          <div className="h-2 rounded bg-surface-2">
            <div className="h-2 rounded bg-navy-2 transition-[width] duration-500" style={{ width: `${(t.count / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ol>
  );
}

/** The cards under the field tiles: whole-university by default, the selected field's view when filtered. */
export function FocusDetails({ fields, rising, topFaculty, byField }: Props) {
  const [field] = useField();
  const reduce = useReducedMotion();
  const selected = field ? fields.find((f) => f.field === field) : undefined;
  const scoped = field ? byField[field] : undefined;
  const subMax = selected?.subfields[0]?.count ?? 1;

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div key={field ?? "all"} className="flex flex-col gap-4"
        initial={reduce ? false : { opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={reduce ? undefined : { opacity: 0, y: -10 }}
        transition={{ duration: 0.25 }}>
        {selected ? (
          <>
            <p role="status" className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl bg-accent-soft px-4 py-3 text-sm text-accent-soft-ink">
              <span><strong>{fmt(selected.count)}</strong> works in {selected.field}. Notable publications and faculty below are filtered too.</span>
              <a href="#notable" className="inline-flex items-center gap-1 font-semibold underline">Publications <ArrowDown aria-hidden="true" size={14} /></a>
              <a href="#faculty" className="inline-flex items-center gap-1 font-semibold underline">Faculty <ArrowDown aria-hidden="true" size={14} /></a>
            </p>
            <div className="grid gap-4 lg:grid-cols-3">
              <Card title={`Subfields of ${selected.field}`} note="Works by subfield of their primary topic.">
                <ol className="flex flex-col gap-2.5">
                  {selected.subfields.slice(0, 8).map((s) => (
                    <li key={s.name} className="flex flex-col gap-1">
                      <div className="flex justify-between gap-3 text-sm"><span>{s.name}</span><span className="tabular font-mono text-muted">{fmt(s.count)}</span></div>
                      <div className="h-2 rounded bg-surface-2"><div className="h-2 rounded bg-accent" style={{ width: `${(s.count / subMax) * 100}%` }} /></div>
                    </li>
                  ))}
                </ol>
              </Card>
              <Card title="Rising in this field" note="Last 12 months against the 12 before, at least 10 recent works.">
                <RisingList items={scoped?.rising ?? []} />
              </Card>
              <Card title="Most published in this field" note="Linked faculty by works in this field. Select a name for the profile.">
                <FacultyBars items={scoped?.top_faculty ?? []} />
              </Card>
            </div>
          </>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            <Card title="Rising topics" note="Last 12 months against the 12 before, topics with at least 40 recent works.">
              <RisingList items={rising.slice(0, 6)} />
            </Card>
            <Card title="Most published faculty" note="Works by faculty matched to an OpenAlex author profile. Select a name for the profile.">
              <FacultyBars items={topFaculty.slice(0, 6)} />
            </Card>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
