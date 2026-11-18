"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

/** The page-wide research-field filter lives in the URL (?field=…) so a filtered view is shareable. */
export function useField(): [string | null, (field: string | null) => void] {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const field = params.get("field");
  const setField = useCallback(
    (next: string | null) => {
      const qs = new URLSearchParams(params.toString());
      if (next) qs.set("field", next);
      else qs.delete("field");
      const s = qs.toString();
      router.replace(s ? `${pathname}?${s}` : pathname, { scroll: false });
    },
    [params, router, pathname],
  );
  return [field, setField];
}
