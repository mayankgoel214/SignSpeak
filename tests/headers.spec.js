import { test, expect } from "@playwright/test";

// The policy is only worth having if it is enforced everywhere the page runs.
// scripts/serve.mjs replays vercel.json's headers locally, so these assertions
// hold in development, in CI and against the deployed site alike — and a change
// that breaks the policy fails here rather than showing a visitor a blank page.

const REQUIRED = {
  "content-security-policy": /default-src 'self'/,
  "x-content-type-options": /^nosniff$/,
  "referrer-policy": /no-referrer/,
  "permissions-policy": /camera=\(self\)/,
};

test.describe("security headers", () => {
  test("the document carries the policy", async ({ page }) => {
    const response = await page.goto("/index.html");
    const headers = response.headers();
    for (const [name, pattern] of Object.entries(REQUIRED)) {
      expect(headers[name], `${name} is ${headers[name]}`).toMatch(pattern);
    }
  });

  test("the policy denies what it should deny", async ({ page }) => {
    const response = await page.goto("/index.html");
    const csp = response.headers()["content-security-policy"];

    // Camera access is the whole product, so it is granted to this origin only.
    expect(response.headers()["permissions-policy"]).toMatch(/microphone=\(\)/);

    // Nothing about this page should be loading from anywhere else, embedding
    // it, or submitting a form from it.
    expect(csp).toMatch(/object-src 'none'/);
    expect(csp).toMatch(/base-uri 'none'/);
    expect(csp).toMatch(/form-action 'none'/);
    expect(csp).toMatch(/frame-ancestors 'none'/);

    // WebAssembly needs its own allowance; a blanket unsafe-eval does not
    // belong on a page with no reason to evaluate strings.
    expect(csp).toMatch(/'wasm-unsafe-eval'/);
    expect(csp, "the policy must not allow arbitrary eval").not.toMatch(/'unsafe-eval'[^-]/);
    expect(csp, "inline styles were removed so the policy can forbid them").not.toMatch(
      /style-src[^;]*'unsafe-inline'/
    );
    expect(csp, "no inline scripts on this page").not.toMatch(/script-src[^;]*'unsafe-inline'/);
  });

  test("the page runs clean under it, with no violations reported", async ({ page }) => {
    const violations = [];
    page.on("console", (m) => {
      if (/Content Security Policy|Refused to/i.test(m.text())) violations.push(m.text());
    });
    await page.goto("/index.html");
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 30_000 });
    await expect(page.locator("#calibration-card")).toBeVisible();
    expect(violations, violations.join("\n")).toEqual([]);
  });

  test("an unknown address gets a real page, not a default", async ({ page }) => {
    const response = await page.goto("/this-does-not-exist");
    expect(response.status()).toBe(404);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Nothing at");
    // And a way back, rather than a dead end.
    await page.getByRole("link", { name: "Go to the demo" }).click();
    await expect(page.locator("#start")).toBeVisible({ timeout: 30_000 });
  });
});
