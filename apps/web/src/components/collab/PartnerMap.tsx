"use client";

import dynamic from "next/dynamic";
import { useRef } from "react";

import { useI18n } from "@/i18n/client";
import type { StatsData } from "@/lib/types";
import { useNearViewport } from "@/lib/useNearViewport";

// Leaflet touches `window` and weighs ~150 KB: load it in the browser, only when the map is near the viewport.
const Inner = dynamic(() => import("./PartnerMapInner"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse rounded-2xl bg-surface-2" />,
});

export function PartnerMap({ partners }: { partners: StatsData["partner_map"] }) {
  const { t } = useI18n();
  const ref = useRef<HTMLDivElement>(null);
  const near = useNearViewport(ref, "600px 0px");
  return (
    <div ref={ref} role="region" aria-label={t.collab.mapLabel(partners.length)}
         className="relative z-0 h-[420px] overflow-hidden rounded-2xl border border-line bg-surface-2">
      {near && <Inner partners={partners} />}
    </div>
  );
}
