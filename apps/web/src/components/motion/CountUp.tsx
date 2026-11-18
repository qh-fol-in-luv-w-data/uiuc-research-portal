"use client";

import { animate, useInView, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";

// Server components pass a format *name*: functions cannot cross the server/client boundary.
type Kind = "int" | "percent";
type Props = { value: number; kind?: Kind; duration?: number; className?: string };

const FORMATS: Record<Kind, (n: number) => string> = {
  int: (n) => Math.round(n).toLocaleString("en-US"),
  percent: (n) => `${n.toFixed(1)}%`,
};

/** Counts up from 0 when scrolled into view. Screen readers always get the final value. */
export function CountUp({ value, kind = "int", duration = 0.9, className }: Props) {
  const format = FORMATS[kind];
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(reduce ? value : 0);

  useEffect(() => {
    if (reduce) {
      setShown(value);
      return;
    }
    if (!inView) return;
    const controls = animate(0, value, { duration, ease: [0.16, 1, 0.3, 1], onUpdate: setShown });
    return () => controls.stop();
  }, [inView, reduce, value, duration]);

  return (
    <span ref={ref} className={className}>
      <span aria-hidden="true">{format(shown)}</span>
      <span className="sr-only">{format(value)}</span>
    </span>
  );
}
