"use client";

import dynamic from "next/dynamic";

import type { StatsData } from "@/lib/types";

// Leaflet touches `window`; load it only in the browser.
const Inner = dynamic(() => import("./PartnerMapInner"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse rounded-2xl bg-surface-2" />,
});

export function PartnerMap({ partners }: { partners: StatsData["partner_map"] }) {
  return (
    <div role="region" aria-label={`Map of the ${partners.length} institutions that co-author most often with UIUC`}
         className="relative z-0 h-[420px] overflow-hidden rounded-2xl border border-line">
      <Inner partners={partners} />
    </div>
  );
}
