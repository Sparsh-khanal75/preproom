import { render, screen } from "@testing-library/react";

import { MarkedText, segment } from "./MarkedText";

describe("segment", () => {
  it("marks each highlight once, case-insensitively, keeping the original text", () => {
    const segs = segment("The fee is £25,000 and NABIL bank pays.", [
      { text: "£25,000", kind: "contradiction" },
      { text: "Nabil Bank", kind: "detail" },
    ]);
    expect(segs.map((s) => s.text).join("")).toBe("The fee is £25,000 and NABIL bank pays.");
    expect(segs.filter((s) => s.mark).map((s) => [s.text, s.mark!.kind])).toEqual([
      ["£25,000", "contradiction"],
      ["NABIL bank", "detail"],
    ]);
  });

  it("resolves overlaps by priority: a contradiction beats a detail on the same words", () => {
    const segs = segment("University of Manchester", [
      { text: "University of Manchester", kind: "detail" },
      { text: "University of Manchester", kind: "contradiction" },
    ]);
    expect(segs).toHaveLength(1);
    expect(segs[0]!.mark!.kind).toBe("contradiction");
  });

  it("ignores highlights that are not in the text", () => {
    expect(segment("hello", [{ text: "missing", kind: "generic" }])).toEqual([{ text: "hello" }]);
  });
});

it("renders marks with their explanation as a tooltip", () => {
  render(<MarkedText text="I am passionate about it" highlights={[{ text: "passionate about", kind: "generic", note: "Sounds memorised" }]} />);
  const mark = screen.getByText("passionate about");
  expect(mark).toHaveClass("mark-generic");
  expect(mark).toHaveAttribute("title", "Generic phrase: Sounds memorised");
});
