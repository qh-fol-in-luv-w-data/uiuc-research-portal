import { ExternalLink } from "lucide-react";

import { dateLabel, fmt } from "@/lib/format";
import type { WorkCard } from "@/lib/types";

export function WorkItem({ work, metric, onAuthor }: {
  work: WorkCard; metric: "cited" | "recent"; onAuthor?: (facultyId: number) => void;
}) {
  const link = work.doi ?? `https://openalex.org/${work.id}`;
  const authors = work.uiuc_authors.slice(0, 4);
  return (
    <article className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-5 gap-y-2 rounded-2xl border border-line bg-surface p-5 transition hover:border-navy-3">
      <h3 className="text-[17px] font-semibold leading-snug">{work.title}</h3>
      <span className="tabular whitespace-nowrap font-mono text-sm font-medium text-accent-ink">
        {metric === "cited" ? `${fmt(work.cited_by_count)} citations` : dateLabel(work.publication_date)}
      </span>
      <p className="text-sm text-muted">
        {[work.venue?.replace(/ \(.*\)$/, ""), work.field, metric === "cited" ? dateLabel(work.publication_date) : null]
          .filter(Boolean).join(" · ")}
        {work.is_oa && <span className="ml-2 rounded-full bg-accent-soft px-2 py-0.5 text-xs text-accent-soft-ink">Open access</span>}
      </p>
      <a href={link} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 self-start text-sm text-accent-ink hover:underline">
        Source <ExternalLink aria-hidden="true" size={14} />
      </a>
      {authors.length > 0 && (
        <p className="col-span-2 text-sm">
          <span className="text-muted">UIUC authors: </span>
          {authors.map((a, i) => (
            <span key={`${a.name}-${i}`}>
              {i > 0 && ", "}
              {a.faculty_id && onAuthor ? (
                <button type="button" onClick={() => onAuthor(a.faculty_id!)} className="font-semibold text-ink underline decoration-accent decoration-2 underline-offset-2 hover:text-accent-ink">
                  {a.name}
                </button>
              ) : (
                <span>{a.name}</span>
              )}
            </span>
          ))}
          {work.uiuc_authors.length > 4 && <span className="text-muted"> and {work.uiuc_authors.length - 4} more</span>}
        </p>
      )}
    </article>
  );
}
