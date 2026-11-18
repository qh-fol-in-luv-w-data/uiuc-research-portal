"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";

import { WorkItem } from "@/components/WorkItem";
import { openFaculty } from "@/lib/facultyEvents";
import type { Page, WorkCard } from "@/lib/types";
import { useField } from "@/lib/useField";

type Tab = "cited" | "recent";
const TABS: { id: Tab; label: string }[] = [{ id: "cited", label: "Most cited" }, { id: "recent", label: "Most recent" }];

export function Notable({ initial }: { initial: Record<Tab, Page<WorkCard>> }) {
  const [tab, setTab] = useState<Tab>("cited");
  const [field] = useField();
  const [data, setData] = useState<Record<string, WorkCard[]>>({ "cited|": initial.cited.items, "recent|": initial.recent.items });
  const [error, setError] = useState(false);
  const reduce = useReducedMotion();
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const key = `${tab}|${field ?? ""}`;

  useEffect(() => {
    if (data[key]) return;
    const qs = new URLSearchParams({ sort: tab, page_size: "6" });
    if (field) qs.set("field", field);
    let alive = true;
    fetch(`/api/works?${qs}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((p: Page<WorkCard>) => alive && setData((d) => ({ ...d, [key]: p.items })))
      .catch(() => alive && setError(true));
    return () => { alive = false; };
  }, [key, tab, field, data]);

  const onKey = (e: React.KeyboardEvent, i: number) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const next = (i + (e.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length;
    setTab(TABS[next].id);
    tabRefs.current[next]?.focus();
  };
  const items = data[key];

  return (
    <div className="flex flex-col gap-4">
      <div role="tablist" aria-label="Sort publications" className="flex self-start rounded-full bg-surface-2 p-1 ring-1 ring-line">
        {TABS.map((t, i) => (
          <button key={t.id} ref={(el) => { tabRefs.current[i] = el; }} type="button" role="tab" id={`tab-${t.id}`}
            aria-selected={tab === t.id} aria-controls="notable-panel" tabIndex={tab === t.id ? 0 : -1}
            onClick={() => setTab(t.id)} onKeyDown={(e) => onKey(e, i)}
            className={`min-h-11 rounded-full px-5 text-sm font-semibold transition ${tab === t.id ? "bg-surface text-ink shadow" : "text-muted hover:text-ink"}`}>
            {t.label}
          </button>
        ))}
      </div>
      <div id="notable-panel" role="tabpanel" aria-labelledby={`tab-${tab}`} aria-busy={!items}>
        {error && !items ? (
          <p className="rounded-xl border border-line bg-surface p-5 text-muted">Publications could not be loaded. Reload the page to try again.</p>
        ) : !items ? (
          <div className="flex flex-col gap-3">{[0, 1, 2].map((i) => <div key={i} className="h-28 animate-pulse rounded-2xl bg-surface" />)}</div>
        ) : items.length === 0 ? (
          <p className="rounded-xl border border-line bg-surface p-5 text-muted">No publications in {field} for this view.</p>
        ) : (
          <AnimatePresence mode="wait" initial={false}>
            <motion.ol key={key} className="flex flex-col gap-3"
              initial={reduce ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={reduce ? undefined : { opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}>
              {items.map((w) => <li key={w.id}><WorkItem work={w} metric={tab} onAuthor={openFaculty} /></li>)}
            </motion.ol>
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
