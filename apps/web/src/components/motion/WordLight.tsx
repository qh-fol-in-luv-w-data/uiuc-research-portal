"use client";

import { motion, useReducedMotion, useScroll, useTransform, type MotionValue } from "motion/react";
import { useRef } from "react";

function Word({ word, progress, range }: { word: string; progress: MotionValue<number>; range: [number, number] }) {
  const opacity = useTransform(progress, range, [0.28, 1]);
  return <motion.span style={{ opacity }}>{word} </motion.span>;
}

/** Words light up as the paragraph scrolls through the viewport (scroll-linked). */
export function WordLight({ text, className }: { text: string; className?: string }) {
  const ref = useRef<HTMLParagraphElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 0.9", "start 0.45"] });
  const words = text.split(" ");
  if (reduce) return <p className={className}>{text}</p>;
  return (
    <p ref={ref} className={className} aria-label={text}>
      <span aria-hidden="true">
        {words.map((w, i) => (
          <Word key={`${w}-${i}`} word={w} progress={scrollYProgress}
                range={[i / words.length, Math.min(1, (i + 1.5) / words.length)]} />
        ))}
      </span>
    </p>
  );
}
