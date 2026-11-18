import type { CSSProperties, ReactNode } from "react";

/**
 * Fade-up as the element enters the viewport, via CSS scroll-driven animation (see globals.css).
 * Content is visible by default: browsers without animation-timeline, reduced motion, screenshots
 * and no-JS all get the final state. `delay` (seconds) staggers siblings.
 */
export function Reveal({ children, delay = 0, className, as: Tag = "div" }: {
  children: ReactNode; delay?: number; className?: string; as?: "div" | "li" | "article" | "section";
}) {
  return (
    <Tag className={`reveal ${className ?? ""}`} style={{ "--d": delay } as CSSProperties}>
      {children}
    </Tag>
  );
}
