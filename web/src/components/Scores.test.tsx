import { render, screen } from "@testing-library/react";

import { SubscoreBars } from "./Scores";

it("shows each sub-score and a dash for ones that don't apply", () => {
  render(<SubscoreBars subscores={{ consistency: 9.8, specificity: 4.2, relevance: 7, fluency: null, language: 7.2 }} />);
  expect(screen.getByRole("meter", { name: "Consistency" })).toHaveAttribute("aria-valuenow", "9.8");
  expect(screen.getByText("4.2")).toHaveClass("text-flag");
  expect(screen.queryByRole("meter", { name: "Fluency" })).toBeNull();
  expect(screen.getByText("—")).toBeInTheDocument();
});
