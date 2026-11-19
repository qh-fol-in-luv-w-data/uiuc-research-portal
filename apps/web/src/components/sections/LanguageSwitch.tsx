"use client";

import { Languages } from "lucide-react";

import { useI18n } from "@/i18n/client";

/** Links to the other language, keeping the field filter and section anchor; remembers the choice for "/". */
export function LanguageSwitch() {
  const { lang, t } = useI18n();
  const other = lang === "en" ? "vi" : "en";
  const go = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    document.cookie = `lang=${other}; path=/; max-age=31536000; samesite=lax`;
    window.location.assign(`/${other}${window.location.search}${window.location.hash}`);
  };
  return (
    <a href={`/${other}`} hrefLang={other} lang={other} onClick={go} aria-label={t.header.switchLabel}
       className="inline-flex min-h-11 items-center gap-1.5 rounded-full border border-white/20 px-3 text-sm text-hero-muted transition-colors hover:border-white/50 hover:text-hero-ink">
      <Languages aria-hidden="true" size={16} />
      {t.header.switchTo}
    </a>
  );
}
