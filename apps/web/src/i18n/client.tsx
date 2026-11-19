"use client";

import { createContext, useContext, useMemo } from "react";

import { DICTS, formatters, type Locale } from "./dict";

const LangContext = createContext<Locale>("en");

/** Only the language code crosses the server/client boundary; dictionaries hold functions, so each side builds its own. */
export function I18nProvider({ lang, children }: { lang: Locale; children: React.ReactNode }) {
  return <LangContext value={lang}>{children}</LangContext>;
}

export function useI18n() {
  const lang = useContext(LangContext);
  return useMemo(() => ({ lang, t: DICTS[lang], f: formatters(lang) }), [lang]);
}
