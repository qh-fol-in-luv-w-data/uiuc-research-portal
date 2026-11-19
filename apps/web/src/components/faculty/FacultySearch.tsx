"use client";

import { Search } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";

import { openFaculty } from "@/lib/facultyEvents";
import { useI18n } from "@/i18n/client";
import type { FacultyCard, Page } from "@/lib/types";
import { useField } from "@/lib/useField";

import { Avatar } from "./Avatar";

const POSITIONS = ["", "Professor", "Associate Professor", "Assistant Professor"];

export function FacultySearch() {
  const { t, f } = useI18n();
  const [query, setQuery] = useState(t.facultySearch.initial);
  const [debounced, setDebounced] = useState(query);
  const [position, setPosition] = useState("");
  const [field] = useField();
  const [result, setResult] = useState<Page<FacultyCard> | null>(null);
  const [error, setError] = useState(false);
  const reduce = useReducedMotion();

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 300);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    const qs = new URLSearchParams({ page_size: "12" });
    if (debounced) qs.set("q", debounced);
    if (position) qs.set("position", position);
    if (field) qs.set("field", field);
    const ctrl = new AbortController();
    setError(false);
    fetch(`/api/faculty?${qs}`, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setResult)
      .catch((e) => { if (e?.name !== "AbortError") setError(true); });
    return () => ctrl.abort();
  }, [debounced, position, field]);

  return (
    <div className="flex flex-col gap-5">
      <form role="search" onSubmit={(e) => e.preventDefault()} className="flex flex-wrap gap-2.5">
        <label htmlFor="faculty-q" className="sr-only">{t.facultySearch.label}</label>
        <div className="relative min-w-0 flex-[999_1_320px]">
          <Search aria-hidden="true" size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted" />
          <input id="faculty-q" type="search" value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder={t.facultySearch.placeholder}
            className="h-13 w-full rounded-xl border border-line bg-surface pl-11 pr-4 text-base text-ink placeholder:text-muted" />
        </div>
        <label htmlFor="faculty-pos" className="sr-only">{t.facultySearch.position}</label>
        <select id="faculty-pos" value={position} onChange={(e) => setPosition(e.target.value)}
          className="h-13 flex-[1_1_180px] rounded-xl border border-line bg-surface px-3 text-ink">
          {POSITIONS.map((p) => <option key={p} value={p}>{p ? t.facultySearch.positions[p] ?? p : t.facultySearch.anyPosition}</option>)}
        </select>
      </form>
      <div className="flex flex-wrap gap-2" aria-label={t.facultySearch.examples}>
        {t.facultySearch.suggestions.map((s) => (
          <button key={s} type="button" onClick={() => setQuery(s)}
            className="min-h-9 rounded-full border border-line bg-surface px-3.5 text-sm text-ink hover:border-accent">{s}</button>
        ))}
      </div>
      <p className="text-sm text-muted" aria-live="polite">
        {error ? t.facultySearch.unavailable :
          result ? t.facultySearch.count(f.fmt(result.total), field ? f.field(field) : null,
                                         result.total > result.items.length ? result.items.length : null) : t.facultySearch.searching}
      </p>
      {result && result.items.length === 0 && (
        <p className="rounded-xl border border-line bg-surface p-5 text-muted">{t.facultySearch.none(debounced)}</p>
      )}
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {result?.items.map((fc, i) => (
          <motion.li key={fc.id} initial={reduce ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                     transition={{ duration: 0.35, delay: reduce ? 0 : i * 0.04 }}>
            <button type="button" onClick={() => openFaculty(fc.id)}
              className="flex h-full w-full flex-col gap-3 rounded-2xl border border-line bg-surface p-4 text-left transition hover:-translate-y-0.5 hover:border-navy-3 hover:shadow-lg">
              <span className="flex items-center gap-3">
                <Avatar name={fc.name} url={fc.photo_url} />
                <span className="flex min-w-0 flex-col">
                  <span className="font-semibold">{fc.name}</span>
                  <span className="line-clamp-1 text-sm text-muted">{[fc.position, f.field(fc.primary_field)].filter(Boolean).join(" · ")}</span>
                </span>
              </span>
              <span className="flex flex-wrap gap-1.5">
                {(fc.matched_keywords.length ? fc.matched_keywords : fc.keywords).slice(0, 3).map((k) => (
                  <span key={k} className="rounded-full bg-accent-soft px-2.5 py-1 text-xs text-accent-soft-ink">{k}</span>
                ))}
              </span>
              {fc.link_confidence !== null && (
                <span className="tabular mt-auto font-mono text-xs text-muted">{t.facultySearch.link} · {fc.link_confidence.toFixed(2)}</span>
              )}
            </button>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}
