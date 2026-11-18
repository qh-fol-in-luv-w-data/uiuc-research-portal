import { describe, expect, it } from "vitest";

import { citationParts, SSEParser } from "./sse";

describe("SSEParser", () => {
  it("parses events split across chunks", () => {
    const p = new SSEParser();
    expect(p.push('event: plan\ndata: {"intent":"papers","concepts":[],"sort":"recent"}\n\nevent: tok')).toEqual([
      { event: "plan", data: { intent: "papers", concepts: [], sort: "recent" } },
    ]);
    expect(p.push('en\ndata: {"text":"Hi"}\n\n')).toEqual([{ event: "token", data: { text: "Hi" } }]);
  });
  it("skips malformed and data-less blocks", () => {
    expect(new SSEParser().push(": ping\n\nevent: token\ndata: {oops\n\n")).toEqual([]);
  });
});

describe("citationParts", () => {
  it("keeps valid citations and drops out-of-range ones", () => {
    expect(citationParts("A [1] and B [7].", 2)).toEqual([{ text: "A " }, { cite: 1 }, { text: " and B " }, { text: "." }]);
  });
});
