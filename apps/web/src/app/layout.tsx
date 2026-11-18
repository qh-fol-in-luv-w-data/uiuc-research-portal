import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

// IBM Plex (SIL OFL 1.1, see fonts/OFL-LICENSE.txt), self-hosted: builds need no network and
// visitors' browsers make no request to a third-party font CDN.
const plexSans = localFont({
  variable: "--font-plex-sans",
  display: "swap",
  src: [
    { path: "./fonts/ibm-plex-sans-latin-400-normal.woff2", weight: "400" },
    { path: "./fonts/ibm-plex-sans-latin-500-normal.woff2", weight: "500" },
    { path: "./fonts/ibm-plex-sans-latin-600-normal.woff2", weight: "600" },
  ],
});
const plexCondensed = localFont({
  variable: "--font-plex-condensed",
  display: "swap",
  src: [
    { path: "./fonts/ibm-plex-sans-condensed-latin-600-normal.woff2", weight: "600" },
    { path: "./fonts/ibm-plex-sans-condensed-latin-700-normal.woff2", weight: "700" },
  ],
});
const plexMono = localFont({
  variable: "--font-plex-mono",
  display: "swap",
  src: [
    { path: "./fonts/ibm-plex-mono-latin-400-normal.woff2", weight: "400" },
    { path: "./fonts/ibm-plex-mono-latin-500-normal.woff2", weight: "500" },
  ],
});

export const metadata: Metadata = {
  title: "UIUC Research Portal",
  description: "Two years of University of Illinois Urbana-Champaign research, from OpenAlex, with a research assistant.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${plexSans.variable} ${plexCondensed.variable} ${plexMono.variable} antialiased`}>
      <body className="min-h-full font-sans">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-surface focus:px-4 focus:py-2"
        >
          Skip to content
        </a>
        {children}
      </body>
    </html>
  );
}
