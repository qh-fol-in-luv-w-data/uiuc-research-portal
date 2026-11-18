import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CountUp } from "./CountUp";

describe("CountUp", () => {
  it("shows the final value immediately when reduced motion is on", () => {
    render(<CountUp value={23301} />);
    expect(screen.getAllByText("23,301").length).toBeGreaterThan(0);
  });
  it("always exposes the final value to screen readers", () => {
    render(<CountUp value={76.4} kind="percent" />);
    expect(screen.getByText("76.4%", { selector: ".sr-only" })).toBeInTheDocument();
  });
});
