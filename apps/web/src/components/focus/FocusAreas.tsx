import { SectionHeading } from "@/components/SectionHeading";
import type { StatsData } from "@/lib/types";

import { FieldTiles } from "./FieldTiles";
import { FocusDetails } from "./FocusDetails";

export function FocusAreas(props: {
  fields: StatsData["fields"]; rising: StatsData["rising_topics"]; topFaculty: StatsData["top_faculty"]; byField: StatsData["by_field"];
}) {
  return (
    <section id="focus" aria-labelledby="focus-title" className="flex scroll-mt-24 flex-col gap-6 pt-16">
      <SectionHeading id="focus" title="Research focus areas"
        intro="Publications grouped by the OpenAlex field of their primary topic. Tile size follows publication count; select a field to explore it." />
      <FieldTiles fields={props.fields} />
      <FocusDetails {...props} />
    </section>
  );
}
