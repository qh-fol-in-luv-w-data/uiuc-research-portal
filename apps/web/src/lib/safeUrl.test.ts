import { describe, expect, it } from "vitest";

import { safeHref } from "./safeUrl";
import { safeSegment } from "./server/proxy";

describe("safeHref", () => {
  it("keeps http(s) links and drops everything else", () => {
    expect(safeHref("https://doi.org/10.1/x")).toBe("https://doi.org/10.1/x");
    expect(safeHref("javascript:alert(1)")).toBeUndefined();
    expect(safeHref("data:text/html,x")).toBeUndefined();
    expect(safeHref("not a url")).toBeUndefined();
    expect(safeHref(null)).toBeUndefined();
  });
});

describe("safeSegment", () => {
  it("rejects path traversal out of /api", () => {
    expect(["works", "faculty", "42"].every(safeSegment)).toBe(true);
    for (const bad of ["..", ".", "", "a/b", "a\\b", "x?y"]) expect(safeSegment(bad)).toBe(false);
  });
});
