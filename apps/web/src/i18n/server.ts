import { lang } from "next/root-params";

import { DICTS, formatters, hasLocale, type Locale } from "./dict";

/** Strings and formatters for the current route's language (Server Components; reads the [lang] root param). */
export async function getI18n() {
  const value = await lang();
  const locale: Locale = hasLocale(value) ? value : "en";
  return { lang: locale, t: DICTS[locale], f: formatters(locale) };
}
