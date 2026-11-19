import { SectionHeading } from "@/components/SectionHeading";
import { getI18n } from "@/i18n/server";
import type { StatsData } from "@/lib/types";

import { FieldTiles } from "./FieldTiles";
import { FocusDetails } from "./FocusDetails";

export async function FocusAreas(props: {
  fields: StatsData["fields"]; rising: StatsData["rising_topics"]; topFaculty: StatsData["top_faculty"]; byField: StatsData["by_field"];
}) {
  const { t } = await getI18n();
  return (
    <section id="focus" aria-labelledby="focus-title" className="flex scroll-mt-24 flex-col gap-6 pt-16">
      <SectionHeading id="focus" title={t.sections.focus[0]} intro={t.sections.focus[1]} />
      <FieldTiles fields={props.fields} />
      <FocusDetails {...props} />
    </section>
  );
}
