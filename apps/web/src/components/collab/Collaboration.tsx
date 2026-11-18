import Image from "next/image";

import { Reveal } from "@/components/motion/Reveal";
import { SectionHeading } from "@/components/SectionHeading";
import { fmt } from "@/lib/format";
import type { Institution, StatsData } from "@/lib/types";

import { PartnerMap } from "./PartnerMap";

const COUNTRY: Record<string, string> = { US: "United States", CN: "China", FR: "France", DE: "Germany", GB: "United Kingdom", CA: "Canada", JP: "Japan", KR: "South Korea", IN: "India", AU: "Australia", CH: "Switzerland", NL: "Netherlands", IT: "Italy", ES: "Spain", SG: "Singapore", BR: "Brazil", IL: "Israel", SE: "Sweden" };

export function Collaboration({ partners, mapPoints, partnerCount, institution }: {
  partners: StatsData["top_partners"]; mapPoints: StatsData["partner_map"]; partnerCount: number; institution: Institution | null;
}) {
  const photo = institution?.images?.[1] ?? institution?.images?.[0];
  return (
    <section id="collab" aria-labelledby="collab-title" className="cv-auto flex scroll-mt-24 flex-col gap-6">
      <SectionHeading id="collab" title="Collaboration & campus"
        intro={`UIUC co-authored with ${fmt(partnerCount)} other institutions. Illinois institutes such as NCSA and the Carl R. Woese Institute count as UIUC, not as partners.`} />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <Reveal><PartnerMap partners={mapPoints} /></Reveal>
        <Reveal delay={0.08} className="flex flex-col gap-1 rounded-2xl border border-line bg-surface p-5">
          <h3 className="mb-1 text-lg font-semibold">Top partner institutions</h3>
          <ol>
            {partners.slice(0, 8).map((p, i) => (
              <li key={p.id} className="grid grid-cols-[1.5rem_minmax(0,1fr)_auto] gap-x-2 border-t border-line py-2 text-sm first:border-t-0">
                <span className="tabular font-mono text-muted">{i + 1}</span>
                <span className="min-w-0">
                  <span className="block font-medium">{p.name}</span>
                  <span className="text-xs text-muted">{COUNTRY[p.country ?? ""] ?? p.country}</span>
                </span>
                <span className="tabular font-mono text-muted">{fmt(p.count)}</span>
              </li>
            ))}
          </ol>
        </Reveal>
      </div>
      <Reveal className="grid overflow-hidden rounded-2xl border border-line bg-surface md:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
        {photo && (
          <figure className="relative min-h-72">
            <Image src={photo.url} alt={photo.alt} fill sizes="(min-width: 768px) 40vw, 100vw" className="object-cover" />
            <figcaption className="absolute inset-x-0 bottom-0 bg-black/45 px-3 py-1.5 text-[11px] text-white">
              Photo: {photo.author} ({photo.license}), <a href={photo.source} className="underline">Wikimedia Commons</a>
            </figcaption>
          </figure>
        )}
        <div className="flex flex-col gap-4 p-6">
          <h3 className="font-display text-2xl font-bold">{institution?.name ?? "University of Illinois Urbana-Champaign"}</h3>
          {institution?.description && <p className="text-muted">{institution.description}</p>}
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div><dt className="text-muted">Founded</dt><dd className="tabular font-mono text-lg">{institution?.founded}</dd></div>
            <div><dt className="text-muted">Location</dt><dd>{institution?.city}</dd></div>
            <div><dt className="text-muted">Coordinates</dt>
              <dd className="tabular font-mono">{institution?.latitude?.toFixed(3)}° N, {Math.abs(institution?.longitude ?? 0).toFixed(3)}° W</dd></div>
            <div><dt className="text-muted">Web</dt><dd><a href={institution?.homepage ?? "#"} className="text-accent-ink underline">illinois.edu</a></dd></div>
          </dl>
        </div>
      </Reveal>
    </section>
  );
}
