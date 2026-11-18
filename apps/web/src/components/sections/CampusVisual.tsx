import Image from "next/image";

import type { Institution } from "@/lib/types";

/** Campus photo with credit, or a designed placeholder until data/institution.json lists images. */
export function CampusVisual({ institution }: { institution: Institution | null }) {
  const img = institution?.images?.[0];
  if (img) {
    return (
      <figure className="overflow-hidden rounded-2xl border border-white/10 shadow-2xl shadow-black/30">
        <Image src={img.url} alt={img.alt} width={1200} height={750} className="aspect-[16/10] h-auto w-full object-cover" priority />
        <figcaption className="bg-black/40 px-3 py-1.5 text-[11px] text-hero-muted">
          Photo: {img.author}, {img.license}, via Wikimedia Commons
        </figcaption>
      </figure>
    );
  }
  return (
    <div className="grid aspect-[16/10] w-full place-items-center rounded-2xl border border-white/10 bg-[repeating-linear-gradient(135deg,rgba(255,255,255,0.05)_0_14px,transparent_14px_28px)] p-6 text-center text-sm text-hero-muted">
      <div className="flex flex-col items-center gap-2">
        <span className="font-display text-2xl font-bold text-hero-ink">{institution?.city ?? "Urbana–Champaign, Illinois"}</span>
        <span>Founded {institution?.founded ?? 1867}</span>
        <span className="font-mono text-xs">
          {institution?.latitude?.toFixed(2)}° N, {Math.abs(institution?.longitude ?? 0).toFixed(2)}° W
        </span>
      </div>
    </div>
  );
}
