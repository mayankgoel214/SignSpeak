import { test, expect } from "@playwright/test";

test.describe("the page a visitor lands on", () => {
  test("renders, with no console errors", async ({ page }) => {
    const errors = [];
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("pageerror", (e) => errors.push(e.message));

    await page.goto("/index.html");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Sign a letter");
    await expect(page.locator("#start")).toBeEnabled({ timeout: 20_000 });
    expect(errors).toEqual([]);
  });

  test("shows the measured figures, read from the evaluation output", async ({ page }) => {
    await page.goto("/index.html");

    // The signer-independent figure is the headline and must be a real
    // percentage -- a page that silently rendered "NaN%" or "0.0%" would look
    // perfectly fine in a screenshot and be a lie.
    const headline = page.locator("#verdict-value");
    await expect(headline).toHaveText(/^\d{1,3}\.\d%$/, { timeout: 20_000 });
    const honest = parseFloat(await headline.innerText());
    expect(honest).toBeGreaterThan(10);
    expect(honest).toBeLessThan(100);

    // Both protocols are drawn, and the dishonest one must be higher than the
    // honest one or the page is telling a story its own data does not support.
    const values = await page.locator("#comparison .cmp__val").allInnerTexts();
    expect(values).toHaveLength(2);
    const [independent, random] = values.map(parseFloat);
    expect(independent).toBeCloseTo(honest, 1);
    expect(random).toBeGreaterThan(independent);

    // And the gap callout must agree with the two bars rather than being typed in.
    const gap = parseFloat(await page.locator("#comparison .cmp__gap b").innerText());
    expect(gap).toBeCloseTo(random - independent, 1);

    await expect(page.locator(".error-note")).toHaveCount(0);
  });

  test("draws every evidence chart", async ({ page }) => {
    await page.goto("/index.html");
    await expect(page.locator("#folds .dots__pt")).toHaveCount(5, { timeout: 20_000 });
    await expect(page.locator("#folds .minitable tbody tr")).toHaveCount(5);
    await expect(page.locator("#perletter .letters__row")).toHaveCount(24);
    await expect(page.locator("#pairs .pairs__row")).toHaveCount(8);

    // 24 x 24 cells, and the diagonal must be marked as such -- an off-by-one in
    // the matrix would still render a plausible-looking square of colour.
    await expect(page.locator("#matrix td")).toHaveCount(24 * 24);
    await expect(page.locator('#matrix td[data-diag="true"]')).toHaveCount(24);

    // Worst letter first: the per-letter chart is explicitly sorted, and a
    // silent sort regression would leave a chart that still looks right.
    const letters = await page.locator("#perletter .letters__row b").allInnerTexts();
    const accuracies = (await page.locator("#perletter .letters__val").allInnerTexts()).map(parseFloat);
    expect(letters).toHaveLength(24);
    expect(accuracies).toEqual([...accuracies].sort((a, b) => a - b));
  });

  test("draws a reference pose for every letter", async ({ page }) => {
    await page.goto("/index.html");
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 20_000 });
    const captions = await page.locator(".glyphcell figcaption").allInnerTexts();
    expect(captions.some((c) => c.startsWith("A"))).toBe(true);
    expect(captions.some((c) => c.startsWith("J"))).toBe(false);
    expect(captions.some((c) => c.startsWith("Z"))).toBe(false);

    // Every reference canvas must actually have ink on it. An empty canvas
    // renders as a tidy grid of nothing and passes a count assertion.
    const inked = await page.evaluate(() =>
      Array.from(document.querySelectorAll(".glyphcell canvas")).filter((c) => {
        const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
        for (let i = 3; i < d.length; i += 4) if (d[i] > 0) return true;
        return false;
      }).length
    );
    expect(inked).toBe(24);
  });

  test("the alphabet detail panel follows the selection", async ({ page }) => {
    await page.goto("/index.html");
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 20_000 });

    await page.locator('.glyphcell[data-letter="R"]').click();
    await expect(page.locator("#detail-letter")).toHaveText("R");
    await expect(page.locator("#detail-stat")).toHaveText(/%\s+correct on a new signer/);
    await expect(page.locator('.glyphcell[data-letter="R"]')).toHaveAttribute("aria-selected", "true");
    await expect(page.locator('.glyphcell[data-letter="A"]')).toHaveAttribute("aria-selected", "false");
  });

  test("says plainly that nothing is uploaded", async ({ page }) => {
    await page.goto("/index.html");
    await expect(page.locator(".headline-note")).toContainText("Nothing is uploaded");
  });

  test("the page does not scroll sideways at phone width", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/index.html");
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 20_000 });
    // The confusion matrix is deliberately wider than a phone and scrolls inside
    // its own container; the page body must not.
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });
});
