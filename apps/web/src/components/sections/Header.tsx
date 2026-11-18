import { MessageCircle } from "lucide-react";

const LINKS = [
  ["#focus", "Focus areas"],
  ["#output", "Scholarly output"],
  ["#notable", "Notable publications"],
  ["#faculty", "Faculty expertise"],
  ["#collab", "Collaboration"],
] as const;

export function Header() {
  return (
    <header className="sticky top-[env(safe-area-inset-top,0px)] z-40 bg-navy/95 text-hero-ink backdrop-blur supports-[backdrop-filter]:bg-navy/85">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-7 gap-y-2 px-[max(16px,env(safe-area-inset-left,0px))] py-3 sm:px-6">
        <a href="#top" className="flex items-center gap-2.5 font-semibold tracking-wide">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent font-display text-lg font-bold text-navy">I</span>
          UIUC Research Portal
        </a>
        <nav aria-label="Sections" className="hidden flex-1 flex-wrap gap-x-5 gap-y-1 text-sm md:flex">
          {LINKS.map(([href, label]) => (
            <a key={href} href={href} className="text-hero-muted transition-colors hover:text-hero-ink">
              {label}
            </a>
          ))}
        </nav>
        <a
          href="#assistant"
          className="ml-auto inline-flex min-h-11 items-center gap-2 rounded-full bg-accent px-4 text-sm font-semibold text-navy transition-transform hover:-translate-y-0.5 md:ml-0"
        >
          <MessageCircle aria-hidden="true" size={16} />
          Ask the research assistant
        </a>
      </div>
    </header>
  );
}
