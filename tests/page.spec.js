import { test, expect } from "@playwright/test";

test.describe("the page a visitor lands on", () => {
  test("renders, with no console errors", async ({ page }) => {
    const errors = [];
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("pageerror", (e) => errors.push(e.message));

    await page.goto("/index.html");
    await expect(page.getByRole("heading", { name: "SignSpeak", level: 1 })).toBeVisible();
    await expect(page.locator("#start")).toBeEnabled({ timeout: 20_000 });
    expect(errors).toEqual([]);
  });

  test("shows the measured figures, read from the evaluation output", async ({ page }) => {
    await page.goto("/index.html");
    const figures = page.locator("#numbers .figure-value");
    await expect(figures).toHaveCount(3, { timeout: 20_000 });

    // The signer-independent figure leads, and it must be a real percentage --
    // a page that silently rendered "NaN%" or "0.0%" would look fine in a
    // screenshot and be a lie.
    const headline = await figures.first().innerText();
    expect(headline).toMatch(/^\d{1,3}\.\d%$/);
    const value = parseFloat(headline);
    expect(value).toBeGreaterThan(10);
    expect(value).toBeLessThan(100);

    // The dishonest number must be higher than the honest one, or the page is
    // telling a story its own data does not support.
    const leaky = parseFloat(await figures.nth(1).innerText());
    expect(leaky).toBeGreaterThan(value);

    await expect(page.locator("#numbers .error")).toHaveCount(0);
  });

  test("draws a reference pose for every letter", async ({ page }) => {
    await page.goto("/index.html");
    await expect(page.locator(".chart-cell")).toHaveCount(24, { timeout: 20_000 });
    const captions = await page.locator(".chart-cell figcaption").allInnerTexts();
    expect(captions).toContain("A");
    expect(captions).not.toContain("J");
    expect(captions).not.toContain("Z");

    // Every reference canvas must actually have ink on it. An empty canvas
    // renders as a tidy grid of nothing and passes a count assertion.
    const inked = await page.evaluate(() =>
      Array.from(document.querySelectorAll(".chart-cell canvas")).filter((c) => {
        const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
        for (let i = 3; i < d.length; i += 4) if (d[i] > 0) return true;
        return false;
      }).length
    );
    expect(inked).toBe(24);
  });

  test("says plainly that nothing is uploaded", async ({ page }) => {
    await page.goto("/index.html");
    await expect(page.locator(".lede")).toContainText("No frame of video leaves your device");
  });
});
