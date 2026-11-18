/**
 * Words light up as the paragraph scrolls into view (epic-design "word-by-word scroll lighting").
 * Pure CSS scroll-driven animation (animation-timeline: view()): no JavaScript, runs off the main
 * thread. Browsers without support, and reduced-motion users, see the plain paragraph.
 */
export function WordLight({ text, className }: { text: string; className?: string }) {
  const words = text.split(" ");
  return (
    <p className={`word-light ${className ?? ""}`}>
      {words.map((w, i) => (
        <span key={`${w}-${i}`} style={{ "--p": (i / words.length).toFixed(3) } as React.CSSProperties}>
          {w}{i < words.length - 1 ? " " : ""}
        </span>
      ))}
    </p>
  );
}
