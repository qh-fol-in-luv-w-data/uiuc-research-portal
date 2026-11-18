"use client";

import { motion, useReducedMotion } from "motion/react";

import { fmt } from "@/lib/format";
import type { StatsData } from "@/lib/types";
import { useField } from "@/lib/useField";

const SHADES = ["bg-navy", "bg-navy-2", "bg-navy-2", "bg-navy-2", "bg-navy-3"];

export function FieldTiles({ fields }: { fields: StatsData["fields"] }) {
  const [field, setField] = useField();
  const reduce = useReducedMotion();
  const shown = fields.slice(0, 12);
  return (
    <div className="flex flex-col gap-3">
      <div className="flex min-h-11 flex-wrap items-center gap-3">
        {field ? (
          <button
            type="button"
            onClick={() => setField(null)}
            className="inline-flex min-h-11 items-center gap-2 rounded-full border border-line bg-surface px-4 text-sm font-medium text-ink hover:border-accent"
          >
            Showing <strong>{field}</strong> across the page · Clear filter
          </button>
        ) : (
          <p className="text-sm text-muted">Select a field to filter notable publications and faculty below.</p>
        )}
      </div>
      <ul className="flex flex-wrap gap-1.5" aria-label="Research fields by number of publications">
        {shown.map((f, i) => {
          const on = field === f.field;
          const dim = field !== null && !on;
          return (
            <motion.li
              key={f.field}
              layout={!reduce}
              initial={reduce ? false : { opacity: 0, scale: 0.94 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.45, delay: reduce ? 0 : i * 0.04, ease: [0.22, 1, 0.36, 1] }}
              style={{ flex: `${f.count} 1 ${Math.max(150, Math.round(f.count / 14))}px` }}
              className="min-w-0"
            >
              <button
                type="button"
                aria-pressed={on}
                onClick={() => setField(on ? null : f.field)}
                className={`flex h-full w-full flex-col items-start justify-end gap-1 rounded-xl p-4 text-left transition duration-300 hover:-translate-y-[3px] hover:shadow-lg ${
                  on ? "bg-accent text-navy" : `${SHADES[Math.min(i, SHADES.length - 1)]} text-hero-ink`
                } ${dim ? "opacity-45" : ""} ${i < 4 ? "min-h-32" : "min-h-24"}`}
              >
                <span className="text-[15px] font-semibold leading-snug">{f.field}</span>
                <span className="tabular font-mono text-[13px] opacity-85">{fmt(f.count)} works</span>
                <span className="line-clamp-1 text-xs opacity-80">Top: {f.subfields[0]?.name}</span>
              </button>
            </motion.li>
          );
        })}
      </ul>
    </div>
  );
}
