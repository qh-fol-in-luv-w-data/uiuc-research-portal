import "server-only";

import { connection } from "next/server";

import { apiBase } from "@/lib/api";

const PASS_HEADERS = ["content-type", "cache-control"];
const MAX_BODY = 64 * 1024; // a chat request (question + 8 history turns) is well under this

/** One path segment of /api/<segments>: no traversal ("..", encoded slashes) out of the API prefix. */
export const safeSegment = (s: string) => s !== "" && s !== "." && s !== ".." && !/[/\\?#]/.test(s);

/** Forward a browser request to the FastAPI service. Streams the body (needed for SSE chat). */
export async function proxy(request: Request, path: string): Promise<Response> {
  await connection();
  const url = new URL(request.url);
  let body: string | undefined;
  if (request.method !== "GET" && request.method !== "HEAD") {
    if (Number(request.headers.get("content-length") ?? 0) > MAX_BODY) return tooLarge();
    body = await request.text();
    if (body.length > MAX_BODY) return tooLarge();
  }
  const target = `${apiBase()}${path}${url.search}`;
  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers: { "content-type": request.headers.get("content-type") ?? "application/json" },
      body,
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

const tooLarge = () => Response.json({ error: "too_large", detail: "Request body too large." }, { status: 413 });
