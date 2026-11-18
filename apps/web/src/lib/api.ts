import "server-only";

import { cacheLife } from "next/cache";

import type { Overview, Page, StatsData, StatsKey, WorkCard } from "./types";

/** Read at call time so one build works against any API address (Docker, local, CI). */
export const apiBase = () => process.env.API_URL ?? "http://localhost:8010";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiGet<T>(path: string, fetcher: typeof fetch = fetch): Promise<T> {
  let res: Response;
  try {
    res = await fetcher(`${apiBase()}${path}`);
  } catch {
    throw new ApiError(503, "unavailable", "The data service is not reachable.");
  }
  if (!res.ok) {
    let body: { error?: string; detail?: string } = {};
    try {
      body = await res.json();
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, body.error ?? "error", body.detail ?? res.statusText);
  }
  return (await res.json()) as T;
}

export async function getOverview(): Promise<Overview> {
  "use cache";
  cacheLife("hours");
  return apiGet<Overview>("/api/overview");
}

export async function getStats<K extends StatsKey>(key: K): Promise<StatsData[K]> {
  "use cache";
  cacheLife("hours");
  const payload = await apiGet<{ data: StatsData[K] }>(`/api/stats/${key}`);
  return payload.data;
}

export async function getWorks(params: { sort: "recent" | "cited"; field?: string; pageSize?: number }) {
  "use cache";
  cacheLife("hours");
  const qs = new URLSearchParams({ sort: params.sort, page_size: String(params.pageSize ?? 6) });
  if (params.field) qs.set("field", params.field);
  return apiGet<Page<WorkCard>>(`/api/works?${qs}`);
}
