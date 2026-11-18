import { act, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useField } from "./useField";

function Probe({ id }: { id: string }) {
  const [field, setField] = useField();
  return <button onClick={() => setField(field ? null : "Medicine")}>{id}:{field ?? "none"}</button>;
}

describe("useField", () => {
  it("writes the field to the URL and updates every subscriber", () => {
    render(<><Probe id="a" /><Probe id="b" /></>);
    act(() => screen.getByText("a:none").click());
    expect(window.location.search).toBe("?field=Medicine");
    expect(screen.getByText("b:Medicine")).toBeInTheDocument();
    act(() => screen.getByText("a:Medicine").click());
    expect(window.location.search).toBe("");
  });
});
