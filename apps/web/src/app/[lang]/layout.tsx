import type { Metadata } from "next";
import localFont from "next/font/local";

import "../globals.css";
import { I18nProvider } from "@/i18n/client";
import { LOCALES } from "@/i18n/dict";
import { getI18n } from "@/i18n/server";

// IBM Plex (SIL OFL 1.1, see fonts/OFL-LICENSE.txt), self-hosted: builds need no network and
// visitors' browsers make no request to a third-party font CDN. The Latin files lack Vietnamese letters (ơ, ư, ạ, ế…):
// the *-vi families come first in the font stack, limited by unicode-range to those letters (downloaded only when a
// page uses them) and without a metric fallback, so every other character falls through to the Latin family.
const plexSans = localFont({
  variable: "--font-plex-sans",
  display: "swap",
  src: [
    { path: "../fonts/ibm-plex-sans-latin-400-normal.woff2", weight: "400" },
    { path: "../fonts/ibm-plex-sans-latin-500-normal.woff2", weight: "500" },
    { path: "../fonts/ibm-plex-sans-latin-600-normal.woff2", weight: "600" },
  ],
});
const plexSansVi = localFont({
  variable: "--font-plex-sans-vi",
  display: "swap",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "unicode-range", value: "U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+0300-0301, U+0303-0304, U+0308-0309, U+0323, U+0329, U+1EA0-1EF9, U+20AB" }],
  src: [
    { path: "../fonts/ibm-plex-sans-vietnamese-400-normal.woff2", weight: "400" },
    { path: "../fonts/ibm-plex-sans-vietnamese-500-normal.woff2", weight: "500" },
    { path: "../fonts/ibm-plex-sans-vietnamese-600-normal.woff2", weight: "600" },
  ],
});
const plexCondensed = localFont({
  variable: "--font-plex-condensed",
  display: "swap",
  src: [
    { path: "../fonts/ibm-plex-sans-condensed-latin-600-normal.woff2", weight: "600" },
    { path: "../fonts/ibm-plex-sans-condensed-latin-700-normal.woff2", weight: "700" },
  ],
});
const plexCondensedVi = localFont({
  variable: "--font-plex-condensed-vi",
  display: "swap",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "unicode-range", value: "U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+0300-0301, U+0303-0304, U+0308-0309, U+0323, U+0329, U+1EA0-1EF9, U+20AB" }],
  src: [
    { path: "../fonts/ibm-plex-sans-condensed-vietnamese-600-normal.woff2", weight: "600" },
    { path: "../fonts/ibm-plex-sans-condensed-vietnamese-700-normal.woff2", weight: "700" },
  ],
});
const plexMono = localFont({
  variable: "--font-plex-mono",
  display: "swap",
  src: [
    { path: "../fonts/ibm-plex-mono-latin-400-normal.woff2", weight: "400" },
    { path: "../fonts/ibm-plex-mono-latin-500-normal.woff2", weight: "500" },
  ],
});
const plexMonoVi = localFont({
  variable: "--font-plex-mono-vi",
  display: "swap",
  preload: false,
  adjustFontFallback: false,
  declarations: [{ prop: "unicode-range", value: "U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+0300-0301, U+0303-0304, U+0308-0309, U+0323, U+0329, U+1EA0-1EF9, U+20AB" }],
  src: [
    { path: "../fonts/ibm-plex-mono-vietnamese-400-normal.woff2", weight: "400" },
    { path: "../fonts/ibm-plex-mono-vietnamese-500-normal.woff2", weight: "500" },
  ],
});
const FONT_VARS = [plexSans, plexSansVi, plexCondensed, plexCondensedVi, plexMono, plexMonoVi].map((f) => f.variable).join(" ");

export async function generateStaticParams() {
  return LOCALES.map((lang) => ({ lang }));
}

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return {
    title: t.meta.title,
    description: t.meta.description,
    alternates: { languages: { en: "/en", vi: "/vi" } },
  };
}

export default async function RootLayout({ children }: LayoutProps<"/[lang]">) {
  const { lang, t } = await getI18n();
  return (
    <html lang={lang} className={`${FONT_VARS} antialiased`}>
      <body className="min-h-full font-sans">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-surface focus:px-4 focus:py-2"
        >
          {t.skip}
        </a>
        <I18nProvider lang={lang}>{children}</I18nProvider>
      </body>
    </html>
  );
}
