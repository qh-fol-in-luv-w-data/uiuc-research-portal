import { connection } from "next/server";
import { Suspense } from "react";

import { Assistant } from "@/components/assistant/Assistant";
import { AssistantButton } from "@/components/assistant/AssistantButton";
import { Collaboration } from "@/components/collab/Collaboration";
import { FacultyDrawer } from "@/components/faculty/FacultyDrawer";
import { FacultySearch } from "@/components/faculty/FacultySearch";
import { FocusAreas } from "@/components/focus/FocusAreas";
import { Notable } from "@/components/notable/Notable";
import { Output } from "@/components/output/Output";
import { SectionHeading } from "@/components/SectionHeading";
import { Header } from "@/components/sections/Header";
import { Hero } from "@/components/sections/Hero";
import { SectionError } from "@/components/sections/SectionError";
import { getI18n } from "@/i18n/server";
import { getOverview, getStats, getWorks } from "@/lib/api";

// Every data section waits for a request (connection()) so builds never need the API;
// results are cached for an hour by the "use cache" fetchers in lib/api.ts.

async function HeroData() {
  await connection();
  try {
    return <Hero overview={await getOverview()} />;
  } catch {
    return <div className="bg-navy px-6 py-16"><SectionError what={(await getI18n()).t.errors.overview} /></div>;
  }
}

async function FocusData() {
  await connection();
  try {
    const [fields, rising, topFaculty, byField] = await Promise.all([
      getStats("fields"), getStats("rising_topics"), getStats("top_faculty"), getStats("by_field")]);
    return <FocusAreas fields={fields} rising={rising} topFaculty={topFaculty} byField={byField} />;
  } catch {
    return <SectionError what={(await getI18n()).t.sections.focus[0]} />;
  }
}

async function OutputData() {
  await connection();
  try {
    const [monthly, types, venues, overview] = await Promise.all([getStats("monthly"), getStats("types"), getStats("top_venues"), getOverview()]);
    return <Output monthly={monthly} types={types} venues={venues} oaShare={overview.oa_share} />;
  } catch {
    return <SectionError what={(await getI18n()).t.sections.output[0]} />;
  }
}

async function NotableData() {
  await connection();
  try {
    const [cited, recent] = await Promise.all([getWorks({ sort: "cited" }), getWorks({ sort: "recent" })]);
    return <Notable initial={{ cited, recent }} />;
  } catch {
    return <SectionError what={(await getI18n()).t.sections.notable[0]} />;
  }
}

async function CollabData() {
  await connection();
  try {
    const [partners, mapPoints, overview] = await Promise.all([getStats("top_partners"), getStats("partner_map"), getOverview()]);
    return <Collaboration partners={partners} mapPoints={mapPoints} partnerCount={overview.partner_institutions} institution={overview.institution} />;
  } catch {
    return <SectionError what={(await getI18n()).t.errors.collab} />;
  }
}

const Skeleton = ({ h = "h-96" }: { h?: string }) => <div aria-hidden="true" className={`${h} animate-pulse rounded-2xl bg-surface`} />;

export default async function Page() {
  const { t } = await getI18n();
  return (
    <>
      <Header />
      <Suspense fallback={<div aria-hidden="true" className="h-[680px] animate-pulse bg-navy" />}>
        <HeroData />
      </Suspense>
      <main id="main" className="mx-auto flex max-w-7xl flex-col gap-24 px-[max(16px,env(safe-area-inset-left,0px))] pb-24 sm:px-6">
        <Suspense fallback={<Skeleton h="h-[560px]" />}><FocusData /></Suspense>
        <Suspense fallback={<Skeleton />}><OutputData /></Suspense>
        <section id="notable" aria-labelledby="notable-title" className="flex scroll-mt-24 flex-col gap-6">
          <SectionHeading id="notable" title={t.sections.notable[0]} intro={t.sections.notable[1]} />
          <Suspense fallback={<Skeleton />}><NotableData /></Suspense>
        </section>
        <section id="faculty" aria-labelledby="faculty-title" className="flex scroll-mt-24 flex-col gap-6">
          <SectionHeading id="faculty" title={t.sections.faculty[0]} intro={t.sections.faculty[1]} />
          <Suspense fallback={<Skeleton />}><FacultySearch /></Suspense>
        </section>
        <Suspense fallback={<Skeleton h="h-[640px]" />}><CollabData /></Suspense>
        <section id="assistant" aria-labelledby="assistant-title" className="flex scroll-mt-24 flex-col gap-6">
          <SectionHeading id="assistant" title={t.sections.assistant[0]} intro={t.sections.assistant[1]} />
          <Assistant />
        </section>
      </main>
      <footer className="bg-navy text-hero-muted">
        <div className="mx-auto flex max-w-7xl flex-wrap justify-between gap-x-6 gap-y-2 px-[max(16px,env(safe-area-inset-left,0px))] py-6 text-sm sm:px-6">
          <span>{t.footer.data} <a href="https://openalex.org" className="underline">OpenAlex</a> {t.footer.rest}</span>
          <span>{t.footer.unofficial}</span>
        </div>
      </footer>
      <FacultyDrawer />
      <AssistantButton />
    </>
  );
}
