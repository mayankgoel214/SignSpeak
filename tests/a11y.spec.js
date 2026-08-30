import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "@playwright/test";
import { installCamera, expectCameraStubbed, WEBKIT_CANNOT_FAKE_A_CAMERA } from "./support/camera.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE = path.join(HERE, "fixtures", "browser-cases.json");
const fixture = fs.existsSync(FIXTURE) ? JSON.parse(fs.readFileSync(FIXTURE, "utf8")) : null;

const scan = (page) =>
  new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();

const summarise = (violations) =>
  violations.map((v) => ({
    id: v.id,
    impact: v.impact,
    help: v.help,
    nodes: v.nodes.slice(0, 3).map((n) => n.target.join(" ")),
  }));

// Two layers. Axe covers the broad, well-defined rules; the hand-written checks
// below cover things a rule engine cannot judge -- whether a focus ring is
// actually visible against this particular dark surface, whether the live
// readout announces itself, and whether the page is usable without a mouse.

test.describe("accessibility", () => {
  test("has no axe violations", async ({ page }) => {
    await page.goto("/index.html");
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 20_000 });

    const { violations } = await scan(page);
    const readable = summarise(violations);
    expect(readable, JSON.stringify(readable, null, 2)).toEqual([]);
  });

  test("has no axe violations at phone width", async ({ page }) => {
    // The layout reflows substantially below 1000px -- the readout becomes a
    // row, the cards stack -- so the desktop pass does not cover it.
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/index.html");
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 20_000 });

    const readable = summarise((await scan(page)).violations);
    expect(readable, JSON.stringify(readable, null, 2)).toEqual([]);
  });

  test("has no axe violations while the camera is live", async ({ browserName, page }) => {
    test.skip(browserName === "webkit", WEBKIT_CANNOT_FAKE_A_CAMERA);
    test.skip(!fixture, "run: python ml/make_browser_fixture.py");

    // The live state is a different page: real predictions, a filled hold ring,
    // a spelled buffer. None of it is covered by scanning the idle page.
    const target = fixture.cases.find((c) => c.letter === "L") || fixture.cases[0];
    await installCamera(page, { frames: [target.png_base64], padRatio: fixture.pad_ratio });
    await page.goto("/index.html");
    await expectCameraStubbed(page);
    await page.locator("#start").click();
    await expect(page.locator("#spelled")).toHaveText(target.letter, { timeout: 60_000 });

    const readable = summarise((await scan(page)).violations);
    expect(readable, JSON.stringify(readable, null, 2)).toEqual([]);
  });

  test("a focused control is visibly focused", async ({ page }) => {
    await page.goto("/index.html");
    // On a dark theme an inherited default outline can be effectively invisible,
    // which passes every rule engine and helps nobody.
    const ring = await page.locator("#start").evaluate((el) => {
      el.focus();
      const s = getComputedStyle(el);
      return {
        focused: el === document.activeElement,
        width: parseFloat(s.outlineWidth),
        style: s.outlineStyle,
      };
    });
    expect(ring.focused).toBe(true);
    expect(ring.style).not.toBe("none");
    expect(ring.width).toBeGreaterThanOrEqual(2);
  });

  test("tabbing reaches the start button", async ({ browserName, page }) => {
    // Safari's Tab order excludes buttons unless the user turns on "Press Tab to
    // highlight each item", and Playwright's WebKit models that. There is nothing
    // more correct to write than the native <button> already there, so this
    // asserts the behaviour where the platform allows it -- and the page offers
    // the Space shortcut, tested below, as the path that works everywhere.
    test.skip(browserName === "webkit", "WebKit's default Tab order excludes buttons");

    await page.goto("/index.html");
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 20_000 });
    await page.locator("body").press("Tab");
    let reached = false;
    for (let i = 0; i < 12; i++) {
      if (await page.locator("#start").evaluate((el) => el === document.activeElement)) {
        reached = true;
        break;
      }
      await page.keyboard.press("Tab");
    }
    expect(reached, "the start button was not reachable by tabbing").toBe(true);
  });

  test("the documented Space shortcut is wired, with nothing focused", async ({ browserName, page }) => {
    test.skip(browserName === "webkit", WEBKIT_CANNOT_FAKE_A_CAMERA);
    test.skip(!fixture, "run: python ml/make_browser_fixture.py");

    // The page tells the visitor Space starts and stops the camera. That claim is
    // the keyboard path on platforms whose Tab order will not reach a button, so
    // it has to work with no element focused at all.
    const target = fixture.cases.find((c) => c.letter === "L") || fixture.cases[0];
    await installCamera(page, { frames: [target.png_base64], padRatio: fixture.pad_ratio });
    await page.goto("/index.html");
    await expectCameraStubbed(page);
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 20_000 });

    await page.evaluate(() => document.activeElement instanceof HTMLElement && document.activeElement.blur());
    await page.keyboard.press("Space");
    await expect(page.locator("#device")).toHaveAttribute("data-live", "true", { timeout: 60_000 });
    await page.keyboard.press("Space");
    await expect(page.locator("#device")).toHaveAttribute("data-live", "false");
  });

  test("the alphabet grid answers the keyboard", async ({ page }) => {
    await page.goto("/index.html");
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 20_000 });
    const cell = page.locator('.glyphcell[data-letter="V"]');
    await cell.focus();
    await page.keyboard.press("Enter");
    await expect(page.locator("#detail-letter")).toHaveText("V");
    await expect(cell).toHaveAttribute("aria-selected", "true");
  });

  test("the live readout announces itself", async ({ page }) => {
    await page.goto("/index.html");
    await expect(page.locator("#letter")).toHaveAttribute("aria-live", "polite");
    // Cells carry their own description, so the matrix is not colour-only. The
    // first cell is the diagonal, which is worded differently on purpose.
    await expect(page.locator("#matrix td").first()).toHaveAttribute("aria-label", /read correctly/);
    await expect(page.locator("#matrix tbody tr").first().locator("td").nth(1)).toHaveAttribute(
      "aria-label",
      /read as/
    );
  });

  test("body text clears WCAG AA against the surface it sits on", async ({ page }) => {
    await page.goto("/index.html");
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 20_000 });

    const results = await page.evaluate(() => {
      const lum = (c) => {
        const [r, g, b] = c.match(/\d+(\.\d+)?/g).slice(0, 3).map(Number).map((v) => {
          const s = v / 255;
          return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
        });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
      };
      const behind = (el) => {
        for (let n = el; n; n = n.parentElement) {
          const bg = getComputedStyle(n).backgroundColor;
          if (bg && !/rgba\(0, 0, 0, 0\)|transparent/.test(bg)) return bg;
        }
        return "rgb(0, 0, 0)";
      };
      const ratio = (a, b) => {
        const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
        return (hi + 0.05) / (lo + 0.05);
      };
      // One representative of every text role on the page.
      const selectors = [
        ".prose", ".card__note", ".chart__foot", ".figure-note", ".statusstrip",
        ".eyebrow", ".navlinks a", ".letters__val", ".minitable td", ".pairs__val",
        ".buffer__label", ".readout__status", "footer p", ".step p", ".headline-note",
      ];
      const out = [];
      for (const sel of selectors) {
        const el = document.querySelector(sel);
        if (!el) continue;
        const s = getComputedStyle(el);
        const size = parseFloat(s.fontSize);
        const weight = Number(s.fontWeight) || 400;
        const large = size >= 24 || (size >= 18.66 && weight >= 700);
        out.push({
          sel,
          size,
          ratio: Number(ratio(s.color, behind(el)).toFixed(2)),
          required: large ? 3 : 4.5,
        });
      }
      return out;
    });

    const failures = results.filter((r) => r.ratio < r.required);
    expect(failures, JSON.stringify(failures, null, 2)).toEqual([]);
  });
});
