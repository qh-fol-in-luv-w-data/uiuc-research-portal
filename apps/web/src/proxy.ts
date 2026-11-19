import { type NextRequest, NextResponse } from "next/server";

import { hasLocale } from "./i18n/dict";

/** Sends paths without a language prefix to /en or /vi: the visitor's saved choice first, then Accept-Language. */
export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (hasLocale(pathname.split("/")[1])) return;
  const saved = request.cookies.get("lang")?.value;
  const accept = request.headers.get("accept-language") ?? "";
  const lang = hasLocale(saved) ? saved : /^\s*vi\b/i.test(accept) || /(^|,)\s*vi\b[^,]*;q=(1|0\.[5-9])/i.test(accept) ? "vi" : "en";
  return NextResponse.redirect(new URL(`/${lang}${search}`, request.url));
}

export const config = {
  // pages only: not the API proxy, health check, Next internals or static files
  matcher: ["/((?!api/|api$|health|_next/|.*\\..*).*)"],
};
