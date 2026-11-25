import { expect, test } from "@playwright/test";

// Full candidate journey against a running stack (API in mock-LLM mode + worker + web).
test("sign up, fill a profile, do a typed interview and read the marked-up report", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Name").fill("E2E Candidate");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("a-long-e2e-password");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Your progress" })).toBeVisible();

  await page.getByRole("link", { name: "Practise" }).click();
  await page.getByRole("link", { name: /Job interview - behavioural/ }).click();
  await page.getByLabel("Role you are applying for").fill("SOC Analyst");
  await page.getByLabel("Company").fill("Example Bank");
  await page.getByLabel("Most relevant experience").fill("Six-month SOC internship triaging SIEM alerts");
  await page.getByLabel(/Achievement/).fill("Cut false positives by 30% by tuning 12 detection rules");
  await page.getByLabel("Top skills").fill("Splunk\nSysmon");
  await page.getByRole("button", { name: "Save and start the interview" }).click();

  await expect(page.getByText(/Question 1 of/)).toBeVisible();
  await page.getByRole("button", { name: "Type instead" }).click();
  const answer =
    "In my SOC internship at Example Bank I tuned 12 Sysmon detection rules in Splunk, which cut false positives by 30% " +
    "over two months, and I documented each change so the night shift could follow it.";
  await page.getByRole("textbox", { name: "Your answer" }).fill(answer);
  await page.getByRole("button", { name: "Submit answer" }).click();
  await expect(page.getByText(/Question 2 of/)).toBeVisible();

  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "End interview" }).click();

  await expect(page.getByRole("heading", { name: "Your answers, marked up" })).toBeVisible({ timeout: 30_000 });
  await expect(page.locator(".mark-detail").first()).toBeVisible();
  await page.getByRole("button", { name: "Why this score" }).first().click();
  await expect(page.getByText("Specificity").first()).toBeVisible();
});
