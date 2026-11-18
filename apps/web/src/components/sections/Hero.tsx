import { CountUp } from "@/components/motion/CountUp";
import { LineReveal } from "@/components/motion/LineReveal";
import { Parallax } from "@/components/motion/Parallax";
import { Reveal } from "@/components/motion/Reveal";
import type { Overview } from "@/lib/types";

import { CampusVisual } from "./CampusVisual";

export function Hero({ overview }: { overview: Overview }) {
  const linkedPct = ((overview.faculty_linked / overview.faculty) * 100).toFixed(1);
  const kpis = [
    { label: "Publications", value: overview.works, note: "articles, preprints, conference papers, chapters, reviews" },
    { label: "Citations received", value: overview.citations, note: "to those publications, per OpenAlex" },
    { label: "Open access", value: overview.oa_share * 100, note: "free to read at publication", percent: true },
    { label: "Faculty profiles", value: overview.faculty, note: `${overview.faculty_linked} matched to OpenAlex authors (${linkedPct}%)` },
  ];
  return (
    <section id="top" className="relative isolate overflow-hidden bg-navy text-hero-ink">
      {/* depth 0: grid texture */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 opacity-[0.18] [background-image:linear-gradient(var(--hero-muted)_1px,transparent_1px),linear-gradient(90deg,var(--hero-muted)_1px,transparent_1px)] [background-size:48px_48px] [mask-image:radial-gradient(ellipse_at_70%_30%,black,transparent_70%)]" />
      {/* depth 1: glow */}
      {/* radial gradients instead of filter: blur, so the drift animation stays on the compositor */}
      <div aria-hidden="true" className="drift-loop pointer-events-none absolute -right-56 -top-56 -z-10 h-[760px] w-[760px] rounded-full bg-[radial-gradient(closest-side,rgb(255_95_5/0.28),transparent)] will-change-transform" />
      <div aria-hidden="true" className="drift-loop pointer-events-none absolute -bottom-64 -left-48 -z-10 h-[680px] w-[680px] rounded-full bg-[radial-gradient(closest-side,rgb(45_78_133/0.7),transparent)] will-change-transform [animation-delay:-6s]" />

      <div className="mx-auto grid max-w-7xl items-end gap-10 px-[max(16px,env(safe-area-inset-left,0px))] pb-12 pt-14 sm:px-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] lg:pt-20">
        <div className="flex min-w-0 flex-col gap-5">
          <p className="font-mono text-xs uppercase tracking-[0.12em] text-[#ffb48a]">
            University of Illinois Urbana-Champaign · Research profile
          </p>
          <LineReveal
            className="font-display text-[clamp(2.4rem,5.4vw,4rem)] font-bold leading-[1.02] [text-wrap:balance]"
            lines={["What Illinois researchers", "published in the", "last two years"]}
          />
          <Reveal delay={0.45}>
            <p className="max-w-[60ch] text-lg leading-relaxed text-hero-muted">
              Every number on this page is computed from OpenAlex records affiliated with UIUC, linked to{" "}
              {overview.faculty.toLocaleString("en-US")} faculty profiles.
            </p>
          </Reveal>
        </div>
        {/* depth 3: main visual with parallax + float loop */}
        <Parallax speed={0.18} className="min-w-0">
          <div className="float-loop will-change-transform">
            <CampusVisual institution={overview.institution} />
          </div>
        </Parallax>
      </div>

      <ul className="mx-auto grid max-w-7xl grid-cols-1 gap-4 px-[max(16px,env(safe-area-inset-left,0px))] pb-14 sm:grid-cols-2 sm:px-6 lg:grid-cols-4">
        {kpis.map((k, i) => (
          <Reveal as="li" key={k.label} delay={0.5 + i * 0.07}
                  className="flex flex-col gap-1.5 rounded-xl border border-white/10 bg-white/[0.06] p-5">
            <span className="text-sm text-hero-muted">{k.label}</span>
            <CountUp
              value={k.value}
              className="tabular font-display text-4xl font-bold"
              kind={k.percent ? "percent" : "int"}
            />
            <span className="text-[13px] text-hero-muted/80">{k.note}</span>
          </Reveal>
        ))}
      </ul>
    </section>
  );
}
