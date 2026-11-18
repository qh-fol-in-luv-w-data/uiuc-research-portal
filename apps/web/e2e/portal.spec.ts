import { expect, test } from "@playwright/test";

test.describe("portal", () => {
  test("loads every section with real data and no console errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("What Illinois researchers");
    for (const id of ["focus", "output", "notable", "faculty", "collab", "assistant"]) {
      await page.locator(`#${id}-title`).scrollIntoViewIfNeeded();
      await expect(page.locator(`#${id}-title`)).toBeVisible();
    }
    await expect(page.getByText(/could not be loaded/)).toHaveCount(0);
    expect(errors.filter((e) => !e.includes("openstreetmap") && !e.includes("media.academic.online"))).toEqual([]);
  });

  test("field filter is reflected in the URL and narrows publications", async ({ page }) => {
    await page.goto("/");
    await page.locator("#focus").getByRole("button", { name: /^Medicine/ }).click();
    await expect(page).toHaveURL(/field=Medicine/);
    await expect(page.getByRole("heading", { name: "Subfields of Medicine" })).toBeVisible();
    await expect(page.locator("#focus").getByRole("status")).toContainText("works in Medicine");
    await expect(page.locator("#notable-panel article p").first()).toContainText("Medicine");
    await page.getByRole("button", { name: /Clear filter/ }).click();
    await expect(page).not.toHaveURL(/field=/);
  });

  test("publication tabs work with the keyboard", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("tab", { name: "Most cited" }).focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: "Most recent" })).toHaveAttribute("aria-selected", "true");
    await expect(page.locator("#notable-panel article").first()).toBeVisible();
  });

  test("faculty search opens a profile drawer that closes with Escape", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("Search faculty by expertise").fill("computer vision");
    const firstCard = page.locator("#faculty ul li button").first();
    await expect(firstCard).toBeVisible();
    const name = (await firstCard.locator("span.font-semibold").first().textContent())!.trim();
    await firstCard.click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("heading", { level: 2 })).toHaveText(name);
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(firstCard).toBeFocused();
  });

  test("assistant renders streamed plan, sources and cited answer", async ({ page }) => {
    await page.route("**/health", (r) => r.fulfill({ json: { db: true, ollama: true, models: [], missing_models: [] } }));
    const sse = [
      ["plan", { intent: "papers", concepts: [["ai", "machine learning"], ["war", "armed conflict"]], sort: "recent" }],
      ["sources", { sources: [{ n: 1, kind: "work", id: "W1", title: "SmartBook: AI-Assisted Situation Report Generation", meta: "Book chapter · Mar 2025", url: null }] }],
      ["token", { text: "SmartBook drafts situation reports " }],
      ["done", { answer: "SmartBook drafts situation reports for analysts [1]." }],
    ].map(([e, d]) => `event: ${e}\ndata: ${JSON.stringify(d)}\n\n`).join("");
    await page.route("**/api/chat", (r) => r.fulfill({ status: 200, headers: { "content-type": "text/event-stream" }, body: sse }));
    await page.goto("/");
    await page.getByRole("button", { name: "What are the most recent UIUC papers on AI in war conflict?" }).click();
    await expect(page.getByText("intent: papers")).toBeVisible();
    await expect(page.getByText("SmartBook: AI-Assisted Situation Report Generation")).toBeVisible();
    await expect(page.locator("#assistant a", { hasText: "[1]" })).toHaveAttribute("href", /#src-0-1/);
  });

  test("assistant shows offline state when the model server is down", async ({ page }) => {
    await page.route("**/health", (r) => r.fulfill({ json: { db: true, ollama: false, models: [], missing_models: ["qwen3:4b"] } }));
    await page.goto("/");
    await expect(page.getByText(/Assistant offline/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Send question" })).toBeDisabled();
  });

  test("renders final values with reduced motion", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");
    await expect(page.locator("#top li").first()).toContainText(/\d{2},\d{3}/);
  });

  test("phone layout has no horizontal scroll @phone", async ({ page }) => {
    await page.goto("/");
    for (const id of ["focus", "output", "notable", "faculty", "collab", "assistant"]) {
      await page.locator(`#${id}-title`).scrollIntoViewIfNeeded();
    }
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
});
