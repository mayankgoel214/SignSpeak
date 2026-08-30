import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test, expect } from "@playwright/test";
import { installCamera, expectCameraStubbed, WEBKIT_CANNOT_FAKE_A_CAMERA } from "./support/camera.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const IMAGES = path.join(HERE, "fixtures", "browser-cases.json");
const fixture = fs.existsSync(IMAGES) ? JSON.parse(fs.readFileSync(IMAGES, "utf8")) : null;

const MODEL = "**/hand_landmarker.task";

// Starting the camera pulls about 8.7 MB. Two behaviours keep that from reading
// as a broken page, and both are easy to lose in a refactor without any other
// test noticing, because the page still works -- just slowly and silently.

test.describe("loading the tracker", () => {
  test("the page itself stays small: nothing heavy loads until it is wanted", async ({ page }) => {
    const heavy = [];
    page.on("request", (r) => {
      if (/hand_landmarker\.task|vision_wasm/.test(r.url())) heavy.push(r.url());
    });

    await page.goto("/index.html");
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 30_000 });
    await expect(page.locator("#verdict-value")).toHaveText(/%$/);
    await page.waitForTimeout(1500);

    expect(heavy, "the tracker downloaded before anyone asked for it").toEqual([]);
  });

  test("hovering the button starts the download, and clicking does not repeat it", async ({ page }) => {
    const modelRequests = [];
    page.on("request", (r) => {
      if (r.url().includes("hand_landmarker.task")) modelRequests.push(r.url());
    });

    await page.goto("/index.html");
    await expect(page.locator("#start")).toBeEnabled({ timeout: 30_000 });

    await page.locator("#start").hover();
    await expect
      .poll(() => modelRequests.length, { message: "hover did not begin the download", timeout: 20_000 })
      .toBe(1);

    // Whatever happens next, the 8.7 MB must not be fetched twice.
    await page.locator("#start").click();
    await page.waitForTimeout(3000);
    expect(modelRequests).toHaveLength(1);
  });

  test("a slow download reports progress rather than sitting still", async ({ browserName, page }) => {
    test.skip(browserName === "webkit", WEBKIT_CANNOT_FAKE_A_CAMERA);
    test.skip(!fixture, "run: python ml/make_browser_fixture.py");

    // Hold the model back so the loading state is observable in every engine,
    // rather than relying on it being slow by luck.
    await page.route(MODEL, async (route) => {
      await new Promise((r) => setTimeout(r, 1200));
      await route.continue();
    });

    const target = fixture.cases.find((c) => c.letter === "L") || fixture.cases[0];
    await installCamera(page, { frames: [target.png_base64], padRatio: fixture.pad_ratio });
    await page.goto("/index.html");
    await expectCameraStubbed(page);

    const seen = [];
    await page.exposeFunction("__recordStatus", (text) => seen.push(text));
    await page.evaluate(() => {
      const el = document.getElementById("status-text");
      window.__recordStatus(el.textContent);
      new MutationObserver(() => window.__recordStatus(el.textContent)).observe(el, {
        childList: true,
        characterData: true,
        subtree: true,
      });
    });

    await page.locator("#start").click();
    await expect(page.locator("#status")).toHaveAttribute("data-kind", "ok", { timeout: 90_000 });

    // It must say it is loading the tracker, then say something about the model,
    // then go live -- in that order.
    const joined = seen.join(" | ");
    expect(joined, joined).toMatch(/Loading hand tracker/);
    expect(joined, joined).toMatch(/Loading model/);
    expect(seen.at(-1)).toMatch(/Live/);

    // A percentage that runs past 100 would mean the denominator is the
    // compressed length, which is the mistake this code exists to avoid.
    for (const text of seen) {
      const pct = /Loading model (\d+)%/.exec(text);
      if (pct) expect(Number(pct[1])).toBeLessThanOrEqual(100);
    }
  });

  test("the stamped asset sizes match the files actually served", async ({ page }) => {
    // The progress denominator comes from assets.json, written at build time. If
    // it drifts from the real file the counter lies, and nothing else would fail.
    await page.goto("/index.html");
    const sizes = await page.evaluate(() => fetch("./models/assets.json").then((r) => r.json()));
    expect(Object.keys(sizes)).toContain("hand_landmarker.task");

    for (const [name, stamped] of Object.entries(sizes)) {
      const actual = await page.evaluate(
        (n) => fetch(`./models/${n}`).then((r) => r.arrayBuffer()).then((b) => b.byteLength),
        name
      );
      expect(actual, `${name} is ${actual} bytes but assets.json says ${stamped}`).toBe(stamped);
    }
  });
});

test.describe("stopping and starting again", () => {
  test.skip(({ browserName }) => browserName === "webkit", WEBKIT_CANNOT_FAKE_A_CAMERA);
  test.setTimeout(180_000);

  test("survives three cycles, reusing the tracker and releasing the camera each time", async ({ page }) => {
    test.skip(!fixture, "run: python ml/make_browser_fixture.py");

    // Someone will stop the camera and start it again. The tracker is cached
    // across cycles and MediaPipe's video mode wants strictly increasing
    // timestamps, so this is exactly where a restart quietly stops working.
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));

    const modelRequests = [];
    page.on("request", (r) => {
      if (r.url().includes("hand_landmarker.task")) modelRequests.push(r.url());
    });

    const target = fixture.cases.find((c) => c.letter === "L") || fixture.cases[0];
    await installCamera(page, { frames: [target.png_base64], padRatio: fixture.pad_ratio });
    await page.goto("/index.html");
    await expectCameraStubbed(page);

    for (let cycle = 1; cycle <= 3; cycle++) {
      await page.locator("#start").click();
      await expect(page.locator("#status")).toHaveAttribute("data-kind", "ok", { timeout: 90_000 });
      // It must actually be reading the hand each time, not merely look live.
      await expect(page.locator("#letter")).toHaveText(target.letter, { timeout: 40_000 });

      const tracks = await page.evaluate(() =>
        (window.__stubbedTracks || []).map((t) => t.readyState)
      );
      expect(tracks.every((t) => t === "live"), `cycle ${cycle}: camera not live`).toBe(true);

      await page.locator("body").click({ position: { x: 5, y: 5 } });
      await page.keyboard.press("Space");
      await expect(page.locator("#device")).toHaveAttribute("data-live", "false");
      expect(await page.evaluate(() => document.getElementById("video").srcObject)).toBeNull();
    }

    // The 8.7 MB is fetched once for the whole session, not once per start.
    expect(modelRequests).toHaveLength(1);
    expect(errors).toEqual([]);
  });
});
