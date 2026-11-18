import { WordLight } from "@/components/motion/WordLight";

export function SectionHeading({ id, title, intro, children }: { id: string; title: string; intro: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex max-w-3xl flex-col gap-2">
        <h2 id={`${id}-title`} className="font-display text-3xl font-bold tracking-tight sm:text-4xl [text-wrap:balance]">
          {title}
        </h2>
        <WordLight text={intro} className="max-w-[64ch] text-base leading-relaxed text-muted sm:text-lg" />
      </div>
      {children}
    </div>
  );
}
