"use client";

import { X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { WorkItem } from "@/components/WorkItem";
import { FACULTY_EVENT } from "@/lib/facultyEvents";
import type { FacultyProfile } from "@/lib/types";

import { Avatar } from "./Avatar";

const METHOD_LABEL: Record<string, string> = { exact: "exact name", first_last: "first + last name", initial_last: "initial + topic check" };

export function FacultyDrawer() {
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<Element | null>(null);
  const [profile, setProfile] = useState<FacultyProfile | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");

  useEffect(() => {
    const onOpen = (e: Event) => {
      const id = (e as CustomEvent<number>).detail;
      opener.current = document.activeElement;
      setProfile(null);
      setState("loading");
      dialog.current?.showModal();
      fetch(`/api/faculty/${id}`)
        .then((r) => (r.ok ? r.json() : Promise.reject()))
        .then((p: FacultyProfile) => { setProfile(p); setState("idle"); })
        .catch(() => setState("error"));
    };
    window.addEventListener(FACULTY_EVENT, onOpen);
    return () => window.removeEventListener(FACULTY_EVENT, onOpen);
  }, []);

  const close = () => dialog.current?.close();
  const onClose = () => (opener.current as HTMLElement | null)?.focus?.();

  return (
    <dialog ref={dialog} onClose={onClose} aria-labelledby="drawer-title"
      onClick={(e) => { if (e.target === dialog.current) close(); }}
      className="fixed inset-y-0 right-0 left-auto m-0 h-full max-h-none w-full max-w-xl overflow-y-auto bg-surface p-0 text-ink shadow-2xl backdrop:bg-navy/50 backdrop:backdrop-blur-sm open:animate-[drawer-in_.32s_cubic-bezier(.22,1,.36,1)]">
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-surface/95 px-5 py-3 backdrop-blur">
        <span className="text-sm font-medium text-muted">Faculty profile</span>
        <button type="button" onClick={close} aria-label="Close profile"
                className="grid h-11 w-11 place-items-center rounded-lg border border-line hover:border-accent">
          <X aria-hidden="true" size={18} />
        </button>
      </div>
      <div className="flex flex-col gap-6 p-5 pb-10">
        {state === "loading" && <div className="h-40 animate-pulse rounded-xl bg-surface-2" aria-label="Loading profile" />}
        {state === "error" && <p className="text-muted">This profile could not be loaded. Close the panel and try again.</p>}
        {profile && (
          <>
            <div className="flex items-center gap-4">
              <Avatar name={profile.name} url={profile.photo_url} size={72} />
              <div className="flex min-w-0 flex-col gap-1">
                <h2 id="drawer-title" className="font-display text-2xl font-bold">{profile.name}</h2>
                <p className="text-sm text-muted">{[profile.position, profile.primary_field].filter(Boolean).join(" · ")}</p>
              </div>
            </div>
            <p className="rounded-xl bg-surface-2 p-3 text-sm">
              {profile.link_confidence !== null ? (
                <>Matched to OpenAlex by <strong>{METHOD_LABEL[profile.link_method ?? ""] ?? profile.link_method}</strong>, confidence{" "}
                  <span className="tabular font-mono">{profile.link_confidence.toFixed(2)}</span>.{" "}
                  {profile.openalex_author_ids.map((a) => (
                    <a key={a} href={`https://openalex.org/${a}`} target="_blank" rel="noreferrer" className="text-accent-ink underline">{a}</a>
                  ))}</>
              ) : (
                <>Not matched to an OpenAlex author, so only the directory keywords are known.</>
              )}
            </p>
            {profile.topics.length > 0 && (
              <section className="flex flex-col gap-2">
                <h3 className="font-semibold">Topics of recent work</h3>
                <ul className="flex flex-wrap gap-1.5">
                  {profile.topics.map((t) => (
                    <li key={t.name} className="rounded-full bg-navy-2 px-3 py-1 text-xs text-hero-ink">{t.name} · {t.count}</li>
                  ))}
                </ul>
              </section>
            )}
            <section className="flex flex-col gap-2">
              <h3 className="font-semibold">Research keywords</h3>
              <ul className="flex flex-wrap gap-1.5">
                {profile.keywords.slice(0, 24).map((k) => (
                  <li key={k} className="rounded-full bg-accent-soft px-2.5 py-1 text-xs text-accent-soft-ink">{k}</li>
                ))}
              </ul>
            </section>
            {profile.recent_works.length > 0 && (
              <section className="flex flex-col gap-3">
                <h3 className="font-semibold">Recent publications</h3>
                {profile.recent_works.map((w) => <WorkItem key={w.id} work={w} metric="recent" />)}
              </section>
            )}
          </>
        )}
      </div>
    </dialog>
  );
}
