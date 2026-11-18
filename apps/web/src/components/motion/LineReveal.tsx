"use client";

import { motion, useReducedMotion } from "motion/react";

/** Masked line reveal for display headings (epic-design text technique). */
export function LineReveal({ lines, className }: { lines: string[]; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <h1 className={className}>
      {lines.map((line, i) => (
        <span key={line} className="block overflow-hidden pb-[0.06em]">
          {reduce ? (
            <span className="block">{line}</span>
          ) : (
            <motion.span
              className="block"
              initial={{ y: "105%" }}
              animate={{ y: "0%" }}
              transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.1 + i * 0.12 }}
            >
              {line}
            </motion.span>
          )}
        </span>
      ))}
    </h1>
  );
}
