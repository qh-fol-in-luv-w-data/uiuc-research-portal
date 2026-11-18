import { describe, expect, it } from "vitest";

import { ApiError, apiGet } from "./api";

const json = (status: number, body: unknown) =>
  (async () => new Response(JSON.stringify(body), { status })) as unknown as typeof fetch;

describe("apiGet", () => {
  it("returns parsed JSON", async () => {
    expect(await apiGet("/x", json(200, { a: 1 }))).toEqual({ a: 1 });
  });
  it("maps API error bodies to ApiError", async () => {
    await expect(apiGet("/x", json(404, { error: "not_found", detail: "nope" }))).rejects.toMatchObject({
      status: 404, code: "not_found", message: "nope",
    });
  });
  it("maps network failures to a 503 ApiError", async () => {
    const down = (async () => { throw new TypeError("fetch failed"); }) as unknown as typeof fetch;
    await expect(apiGet("/x", down)).rejects.toBeInstanceOf(ApiError);
  });
});
