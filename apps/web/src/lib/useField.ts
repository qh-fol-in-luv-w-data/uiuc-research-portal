"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * Page-wide research-field filter. It lives in the URL (?field=…) so a filtered view is shareable,
 * but filtering is client-side: the URL is written with the History API and components subscribe
 * through a tiny external store (no router navigation, no server re-render).
 */
const listeners = new Set<() => void>();

function read(): string | null {
  return new URL(window.location.href).searchParams.get("field");
}

function subscribe(onChange: () => void) {
  listeners.add(onChange);
  window.addEventListener("popstate", onChange);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("popstate", onChange);
  };
}

export function useField(): [string | null, (field: string | null) => void] {
  const field = useSyncExternalStore(subscribe, read, () => null);
  const setField = useCallback((next: string | null) => {
    const url = new URL(window.location.href);
    if (next) url.searchParams.set("field", next);
    else url.searchParams.delete("field");
    window.history.replaceState(window.history.state, "", url.pathname + url.search + url.hash);
    listeners.forEach((l) => l());
  }, []);
  return [field, setField];
}
