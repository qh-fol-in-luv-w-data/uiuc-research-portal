import { act, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FieldTiles } from "./FieldTiles";
import { FocusDetails } from "./FocusDetails";

const fields = [
  { field: "Medicine", count: 1903, subfields: [{ name: "Public Health", count: 380 }, { name: "Radiology", count: 150 }] },
  { field: "Chemistry", count: 500, subfields: [{ name: "Organic Chemistry", count: 200 }] },
];
const byField = {
  Medicine: {
    rising: [{ id: "T1", name: "Zoonotic diseases", field: "Medicine", recent: 11, prior: 4, growth: 2.4 }],
    top_faculty: [{ id: 7, name: "Edward McAuley", count: 38 }],
  },
};

describe("FocusDetails", () => {
  it("shows the whole university by default and the field's own view after selecting a tile", () => {
    window.history.replaceState(null, "", "/");
    render(<><FieldTiles fields={fields} /><FocusDetails fields={fields} rising={[]} topFaculty={[]} byField={byField} /></>);
    expect(screen.getByText("Rising topics")).toBeInTheDocument();
    act(() => screen.getByRole("button", { name: /^Medicine/ }).click());
    expect(screen.getByText("Subfields of Medicine")).toBeInTheDocument();
    expect(screen.getByText("Public Health")).toBeInTheDocument();
    expect(screen.getByText("Zoonotic diseases")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edward McAuley" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("1,903 works in Medicine");
  });
});
