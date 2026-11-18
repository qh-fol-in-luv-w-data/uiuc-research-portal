import "server-only";

import { connection } from "next/server";

import { apiBase } from "@/lib/api";

const PASS_HEADERS = ["content-type", "cache-control"];

/** Forward a browser request to the FastAPI service. Streams the body (needed for SSE chat). */
export async function proxy(request: Request, path: string): Promise<Response> {
  await connection();
  const url = new URL(request.url);
  const target = `${apiBase()}${path}${url.search}`;
  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers: { "content-type": request.headers.get("content-type") ?? "application/json" },
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
      cache: "no-store",
    });
    const headers = new Headers();
    for (const h of PASS_HEADERS) {
      const v = upstream.headers.get(h);
      if (v) headers.set(h, v);
    }
    return new Response(upstream.body, { status: upstream.status, headers });
  } catch {
    return Response.json({ error: "unavailable", detail: "The data service is not reachable." }, { status: 503 });
  }
}
