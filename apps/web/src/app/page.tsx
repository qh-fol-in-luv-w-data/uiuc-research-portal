import { connection } from "next/server";
import { Suspense } from "react";

import { Header } from "@/components/sections/Header";
import { Hero } from "@/components/sections/Hero";
import { SectionError } from "@/components/sections/SectionError";
import { getOverview } from "@/lib/api";

async function HeroData() {
  await connection(); // data comes from the API at request time (cached for an hour), never at build time
  try {
    return <Hero overview={await getOverview()} />;
  } catch {
    return (
      <div className="bg-navy px-6 py-16">
        <SectionError what="The research overview" />
      </div>
    );
  }
}

function HeroSkeleton() {
  return <div aria-hidden="true" className="h-[640px] animate-pulse bg-navy" />;
}

export default function Page() {
  return (
    <>
      <Header />
      <Suspense fallback={<HeroSkeleton />}>
        <HeroData />
      </Suspense>
      <main id="main" className="mx-auto flex max-w-7xl flex-col gap-20 px-[max(16px,env(safe-area-inset-left,0px))] pb-24 sm:px-6" />
    </>
  );
}
