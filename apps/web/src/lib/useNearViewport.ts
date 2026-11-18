"use client";

import { type RefObject, useEffect, useState } from "react";

/** True once the element comes within `margin` of the viewport (native IntersectionObserver). */
export function useNearViewport(ref: RefObject<Element | null>, margin = "0px"): boolean {
  const [near, setNear] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || near) return;
    if (typeof IntersectionObserver === "undefined") { setNear(true); return; }
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) { setNear(true); io.disconnect(); }
    }, { rootMargin: margin });
    io.observe(el);
    return () => io.disconnect();
  }, [ref, margin, near]);
  return near;
}
