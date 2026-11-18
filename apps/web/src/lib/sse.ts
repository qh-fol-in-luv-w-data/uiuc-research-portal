// Contract for POST /api/chat (implemented in Plan 2b).
export type ChatSource = {
  n: number;
  kind: "work" | "faculty";
  id: string;
  title: string;
  meta: string;
  url: string | null;
};
export type ChatPlan = { intent: "papers" | "faculty" | "both" | "out_of_scope"; concepts: string[][]; sort: string };
export type ChatEvent =
  | { event: "plan"; data: ChatPlan }
  | { event: "sources"; data: { sources: ChatSource[] } }
  | { event: "token"; data: { text: string } }
  | { event: "done"; data: { answer: string } }
  | { event: "error"; data: { detail: string } };

/** Incremental Server-Sent Events parser: feed decoded chunks, get complete events. */
export class SSEParser {
  private buffer = "";

  push(chunk: string): ChatEvent[] {
    this.buffer += chunk.replace(/\r\n/g, "\n");
    const out: ChatEvent[] = [];
    let idx: number;
    while ((idx = this.buffer.indexOf("\n\n")) !== -1) {
      const block = this.buffer.slice(0, idx);
      this.buffer = this.buffer.slice(idx + 2);
      let event = "message";
      const data: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
      }
      if (!data.length) continue;
      try {
        out.push({ event, data: JSON.parse(data.join("\n")) } as ChatEvent);
      } catch {
        /* ignore malformed event */
      }
    }
    return out;
  }
}

/** Split an answer into text and [n] citation parts, dropping citations with no matching source. */
export function citationParts(answer: string, sourceCount: number): ({ text: string } | { cite: number })[] {
  const parts: ({ text: string } | { cite: number })[] = [];
  let last = 0;
  for (const m of answer.matchAll(/\[(\d+)\]/g)) {
    const n = Number(m[1]);
    if (m.index! > last) parts.push({ text: answer.slice(last, m.index) });
    if (n >= 1 && n <= sourceCount) parts.push({ cite: n });
    last = m.index! + m[0].length;
  }
  if (last < answer.length) parts.push({ text: answer.slice(last) });
  return parts;
}
