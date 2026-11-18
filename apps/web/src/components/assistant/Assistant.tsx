"use client";

import { ArrowUp, Loader2, MessageCircle } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";

import { type ChatPlan, type ChatSource, citationParts, SSEParser } from "@/lib/sse";

const REQUIRED = [
  "What are the most recent UIUC papers on AI in war conflict?",
  "Which faculty members work on Computer Vision in Healthcare?",
];

type Turn = { question: string; plan?: ChatPlan; sources: ChatSource[]; answer: string; status: "streaming" | "done" | "error"; error?: string };

export function Assistant() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [online, setOnline] = useState<boolean | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const reduce = useReducedMotion();
  const busy = turns.at(-1)?.status === "streaming";

  useEffect(() => {
    fetch("/health").then((r) => r.json())
      .then((h: { ollama: boolean; missing_models: string[] }) => setOnline(h.ollama && h.missing_models.length === 0))
      .catch(() => setOnline(false));
  }, []);

  const update = (fn: (t: Turn) => Turn) => setTurns((ts) => [...ts.slice(0, -1), fn(ts[ts.length - 1])]);

  async function ask(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    const history = turns.filter((t) => t.status === "done").slice(-2)
      .flatMap((t) => [{ role: "user", content: t.question }, { role: "assistant", content: t.answer }]);
    setTurns((ts) => [...ts, { question: q, sources: [], answer: "", status: "streaming" }]);
    try {
      const res = await fetch("/api/chat", { method: "POST", headers: { "content-type": "application/json" },
                                            body: JSON.stringify({ question: q, history }) });
      if (!res.ok || !res.body) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? "The assistant is not available right now.");
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      const parser = new SSEParser();
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const ev of parser.push(decoder.decode(value, { stream: true }))) {
          if (ev.event === "plan") update((t) => ({ ...t, plan: ev.data }));
          else if (ev.event === "sources") update((t) => ({ ...t, sources: ev.data.sources }));
          else if (ev.event === "token") update((t) => ({ ...t, answer: t.answer + ev.data.text }));
          else if (ev.event === "done") update((t) => ({ ...t, answer: ev.data.answer, status: "done" }));
          else if (ev.event === "error") throw new Error(ev.data.detail);
        }
      }
      update((t) => (t.status === "streaming" ? { ...t, status: "done" } : t));
    } catch (e) {
      update((t) => ({ ...t, status: "error", error: e instanceof Error ? e.message : "Something went wrong." }));
    }
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface">
      <div className="flex items-center gap-3 border-b border-line px-5 py-3">
        <span className="grid h-9 w-9 place-items-center rounded-lg bg-navy text-accent"><MessageCircle aria-hidden="true" size={18} /></span>
        <div className="flex flex-col">
          <span className="font-semibold">Research assistant</span>
          <span className="flex items-center gap-1.5 text-xs text-muted">
            <span className={`h-2 w-2 rounded-full ${online ? "bg-green-600" : online === false ? "bg-accent" : "bg-line"}`} />
            {online === null ? "Checking…" : online ? "Online · answers cite UIUC records only" : "Assistant offline: the local model server is not running"}
          </span>
        </div>
      </div>

      <div className="flex max-h-[640px] min-h-80 flex-col gap-6 overflow-y-auto p-5" aria-live="polite">
        {turns.length === 0 && (
          <div className="flex flex-col gap-3">
            <p className="text-muted">Ask about recent UIUC research, notable publications or faculty expertise. Try:</p>
            <div className="flex flex-wrap gap-2">
              {REQUIRED.map((q) => (
                <button key={q} type="button" onClick={() => ask(q)} disabled={!online}
                  className="min-h-11 rounded-full border border-line bg-surface-2 px-4 text-left text-sm hover:border-accent disabled:opacity-50">{q}</button>
              ))}
            </div>
          </div>
        )}
        <AnimatePresence initial={false}>
          {turns.map((t, ti) => (
            <motion.div key={ti} className="flex flex-col gap-3" initial={reduce ? false : { opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <p className="max-w-[80%] self-end rounded-2xl rounded-br-md bg-navy px-4 py-2.5 text-hero-ink">{t.question}</p>
              {t.plan && t.plan.intent !== "out_of_scope" && (
                <div className="flex flex-wrap gap-1.5 font-mono text-xs text-muted">
                  <span className="rounded-md border border-line px-2 py-0.5">intent: {t.plan.intent}</span>
                  {t.plan.sort && <span className="rounded-md border border-line px-2 py-0.5">sort: {t.plan.sort}</span>}
                  {t.plan.concepts.length > 0 && (
                    <span className="rounded-md border border-line px-2 py-0.5">
                      {t.plan.concepts.map((g) => `[${g.slice(0, 3).join(", ")}${g.length > 3 ? "…" : ""}]`).join(" AND ")}
                    </span>
                  )}
                </div>
              )}
              {t.sources.length > 0 && (
                <ol className="grid gap-2 sm:grid-cols-2">
                  {t.sources.map((s, i) => (
                    <motion.li key={s.n} id={`src-${ti}-${s.n}`} initial={reduce ? false : { opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }}
                               transition={{ delay: reduce ? 0 : i * 0.05 }}
                               className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-2 rounded-xl border border-line bg-surface-2 p-3 text-sm">
                      <span className="font-mono font-medium text-accent-ink">[{s.n}]</span>
                      {s.url ? <a href={s.url} target="_blank" rel="noreferrer" className="font-medium hover:underline">{s.title}</a>
                             : <span className="font-medium">{s.title}</span>}
                      <span />
                      <span className="text-xs text-muted">{s.meta}</span>
                    </motion.li>
                  ))}
                </ol>
              )}
              {t.answer && (
                <p className="max-w-[68ch] whitespace-pre-line leading-relaxed">
                  {citationParts(t.answer, t.sources.length).map((p, i) =>
                    "text" in p ? <span key={i}>{p.text}</span> : (
                      <a key={i} href={`#src-${ti}-${p.cite}`} className="font-mono text-sm text-accent-ink hover:underline">[{p.cite}]</a>
                    ))}
                </p>
              )}
              {t.status === "streaming" && (
                <p className="flex items-center gap-2 text-sm text-muted">
                  <Loader2 aria-hidden="true" size={16} className="animate-spin" />
                  {!t.plan ? "Reading the question…" : !t.sources.length ? "Searching UIUC records…" : "Writing the answer…"}
                </p>
              )}
              {t.status === "error" && <p role="alert" className="rounded-xl bg-accent-soft p-3 text-sm text-accent-soft-ink">{t.error}</p>}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <form onSubmit={(e) => { e.preventDefault(); ask(input); }} className="flex items-end gap-2 border-t border-line p-4">
        <label htmlFor="assistant-input" className="sr-only">Ask the research assistant</label>
        <textarea id="assistant-input" ref={inputRef} rows={1} value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(input); } }}
          placeholder={online === false ? "Start Ollama to use the assistant" : "Ask about UIUC papers or faculty…"}
          className="max-h-40 min-h-12 flex-1 resize-y rounded-xl border border-line bg-surface-2 px-4 py-3 text-ink placeholder:text-muted" />
        <button type="submit" disabled={busy || !input.trim() || online === false} aria-label="Send question"
          className="grid h-12 w-12 place-items-center rounded-xl bg-accent text-navy transition hover:-translate-y-0.5 disabled:opacity-40">
          <ArrowUp aria-hidden="true" size={20} />
        </button>
      </form>
    </div>
  );
}
