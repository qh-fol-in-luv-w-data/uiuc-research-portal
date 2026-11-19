import { MessageCircle } from "lucide-react";

import { getI18n } from "@/i18n/server";

import { LanguageSwitch } from "./LanguageSwitch";

const IDS = ["focus", "output", "notable", "faculty", "collab"] as const;

export async function Header() {
  const { t } = await getI18n();
  return (
    <header className="sticky top-[env(safe-area-inset-top,0px)] z-40 bg-navy text-hero-ink shadow-[0_1px_0_rgb(255_255_255/0.08)]">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-7 gap-y-2 px-[max(16px,env(safe-area-inset-left,0px))] py-3 sm:px-6">
        <a href="#top" className="flex items-center gap-2.5 font-semibold tracking-wide">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent font-display text-lg font-bold text-navy">I</span>
          {t.header.brand}
        </a>
        <nav aria-label={t.header.nav} className="hidden flex-1 flex-wrap gap-x-5 gap-y-1 text-sm md:flex">
          {IDS.map((id) => (
            <a key={id} href={`#${id}`} className="text-hero-muted transition-colors hover:text-hero-ink">
              {t.header.links[id]}
            </a>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2 md:ml-0">
          <LanguageSwitch />
          <a
            href="#assistant"
            className="inline-flex min-h-11 items-center gap-2 rounded-full bg-accent px-4 text-sm font-semibold text-navy transition-transform hover:-translate-y-0.5"
          >
            <MessageCircle aria-hidden="true" size={16} />
            {t.header.ask}
          </a>
        </div>
      </div>
    </header>
  );
}
