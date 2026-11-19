import { expect, type Page, test } from "@playwright/test";

/** Wait until React has hydrated the element (sections hydrate independently); clicking earlier does nothing. */
async function hydrated(page: Page, selector: string) {
  await expect.poll(() => page.evaluate((s) => {
    const el = document.querySelector(s);
    return !!el && Object.keys(el).some((k) => k.startsWith("__reactProps"));
  }, selector), { timeout: 30_000 }).toBe(true);
}

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
    await hydrated(page, "#focus ul button");
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
    await hydrated(page, "[role=tab]");
    await page.getByRole("tab", { name: "Most cited" }).focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: "Most recent" })).toHaveAttribute("aria-selected", "true");
    await expect(page.locator("#notable-panel article").first()).toBeVisible();
  });

  test("faculty search opens a profile drawer that closes with Escape", async ({ page }) => {
    await page.goto("/");
    await hydrated(page, "#faculty-q");
    const results = page.waitForResponse((r) => r.url().includes("/api/faculty?") && r.url().includes("computer+vision"));
    await page.getByLabel("Search faculty by expertise").fill("computer vision");
    await results;
    await expect(page.locator("#faculty ul li").first()).toContainText(/vision/i);
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
    await hydrated(page, "#assistant-input");
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

  test("Vietnamese page: localized UI, field names and assistant request @vi", async ({ page }) => {
    await page.goto("/vi");
    await expect(page.locator("html")).toHaveAttribute("lang", "vi");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Các nhà nghiên cứu Illinois");
    await expect(page.locator("#focus").getByRole("button", { name: /^Y học/ })).toBeVisible();   // Medicine
    await expect(page.getByRole("tab", { name: "Trích dẫn nhiều nhất" })).toBeVisible();
    let body: { lang?: string } = {};
    await page.route("**/api/chat", async (r) => {
      body = r.request().postDataJSON();
      await r.fulfill({ status: 200, headers: { "content-type": "text/event-stream" }, body:
        'event: plan\ndata: {"intent":"faculty","concepts":[["computer vision"]],"sort":"relevance"}\n\n'
        + 'event: sources\ndata: {"sources":[]}\n\nevent: done\ndata: {"answer":"Không có."}\n\n' });
    });
    await page.getByRole("button", { name: "Giảng viên nào nghiên cứu thị giác máy tính trong y tế?" }).click();
    await expect(page.getByText("tìm: giảng viên")).toBeVisible();
    expect(body.lang).toBe("vi");
  });

  test("language switch keeps the field filter and is remembered @vi", async ({ page }) => {
    await page.goto("/en?field=Medicine");
    await hydrated(page, "header a[hreflang]");
    await page.getByRole("link", { name: "Xem bằng tiếng Việt" }).click();
    await expect(page).toHaveURL(/\/vi\?field=Medicine/);
    await page.goto("/");
    await expect(page).toHaveURL(/\/vi$/);
  });
});
