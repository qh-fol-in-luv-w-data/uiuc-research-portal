"use client";

import { useState } from "react";

import { initials } from "@/lib/format";

/** Faculty photo; 105 of 999 profiles have none, and some URLs fail: fall back to initials. */
export function Avatar({ name, url, size = 48 }: { name: string; url: string | null; size?: number }) {
  const [broken, setBroken] = useState(false);
  const style = { width: size, height: size };
  if (url && !broken) {
    // eslint-disable-next-line @next/next/no-img-element -- third-party directory images, unknown sizes
    return <img src={url} alt="" loading="lazy" onError={() => setBroken(true)} style={style}
                className="shrink-0 rounded-full bg-surface-2 object-cover" />;
  }
  return (
    <span aria-hidden="true" style={style}
          className="grid shrink-0 place-items-center rounded-full bg-surface-2 text-sm font-semibold text-navy-2 ring-1 ring-line">
      {initials(name)}
    </span>
  );
}
