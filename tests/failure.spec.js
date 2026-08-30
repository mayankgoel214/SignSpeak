import { test, expect } from "@playwright/test";
import {
  installCamera,
  expectCameraStubbed,
  expectCameraStubWasUsed,
  WEBKIT_CANNOT_FAKE_A_CAMERA,
} from "./support/camera.js";

// Nothing here is a happy path. Each test drives one way the page can fail and
// asserts it fails honestly: an accurate message, a recoverable UI, no camera
// left running, and above all no number invented to fill a gap.

const CAMERA_ERRORS = [
  ["NotAllowedError", "Camera permission refused"],
  ["NotFoundError", "No camera found on this device"],
  ["OverconstrainedError", "No camera found on this device"],
  ["NotReadableError", "The camera is in use by another app"],
];

test.describe("when the camera will not start", () => {
  test.skip(({ browserName }) => browserName === "webkit", WEBKIT_CANNOT_FAKE_A_CAMERA);

  for (const [name, expected] of CAMERA_ERRORS) {
    test(`${name} is reported as "${expected}"`, async ({ page }) => {
      await installCamera(page, { reject: name });
      await page.goto("/index.html");
      await expectCameraStubbed(page);
      await page.locator("#start").click();

      await expect(page.locator("#status")).toHaveAttribute("data-kind", "error", { timeout: 30_000 });
      // If the tracker never initialised, the page fails before it ever asks for
      // a camera and every assertion below would be about the wrong failure.
      await expect(page.locator("#delegate")).toHaveAttribute("data-delegate", /GPU|CPU/, {
        timeout: 30_000,
      });
      await expectCameraStubWasUsed(page);
      await expect(page.locator("#status-text")).toHaveText(expected);
      // The button must come back, or a refused permission is a dead end.
      await expect(page.locator("#start")).toBeEnabled();
      await expect(page.locator("#device")).toHaveAttribute("data-live", "false");
    });
  }

  test("a stream that never sends a frame is reported as such, and released", async ({ page }) => {
    // A camera can be granted and still produce nothing -- a virtual device, a
    // privacy shutter, a driver that hands back a dead track. Waiting on
    // video.play() would hang here for ever with the camera light on.
    await installCamera(page, { deadStream: true });
    await page.goto("/index.html");
    await expectCameraStubbed(page);
    await page.locator("#start").click();

    await expect(page.locator("#status-text")).toHaveText("Camera opened but sent no video", {
      timeout: 40_000,
    });
    await expectCameraStubWasUsed(page);
    await expect(page.locator("#start")).toBeEnabled();
    await expect(page.locator("#device")).toHaveAttribute("data-live", "false");

    // The important half: the page must not hold an open camera behind a
    // failure message.
    const states = await page.evaluate(() => (window.__stubbedTracks || []).map((t) => t.readyState));
    expect(states.length).toBeGreaterThan(0);
    expect(states.every((s) => s === "ended")).toBe(true);
    expect(await page.evaluate(() => document.getElementById("video").srcObject)).toBeNull();
  });
});

test.describe("when the evidence cannot be loaded", () => {
  test("no number is invented to fill the gap", async ({ page }) => {
    await page.route("**/models/results.json", (route) => route.abort());
    await page.goto("/index.html");

    await expect(page.locator("#verdict-sub .error-note")).toBeVisible({ timeout: 20_000 });
    await expect(page.locator("#verdict-value")).toHaveText("—");

    // Not a single figure anywhere: a partly-drawn chart is worse than none,
    // because it looks measured.
    await expect(page.locator("#comparison .cmp__row")).toHaveCount(0);
    await expect(page.locator("#folds .dots__pt")).toHaveCount(0);
    await expect(page.locator("#perletter .letters__row")).toHaveCount(0);
    await expect(page.locator("#matrix td")).toHaveCount(0);
    await expect(page.locator("#pairs .pairs__row")).toHaveCount(0);

    const body = await page.locator("#evidence").innerText();
    expect(body).not.toMatch(/\bNaN\b/);
    expect(body).not.toMatch(/undefined/);
  });

  test("the alphabet still draws, without accuracy it cannot know", async ({ page }) => {
    await page.route("**/models/results.json", (route) => route.abort());
    await page.goto("/index.html");

    // The poses come from the model, not the evaluation, so they must survive.
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 20_000 });
    const captions = await page.locator(".glyphcell figcaption span").allInnerTexts();
    expect(captions.every((c) => c === "")).toBe(true);
    await expect(page.locator("#detail-stat")).toHaveText("");
  });
});

test.describe("when the classifier cannot be loaded", () => {
  test("the demo disables itself and says why", async ({ page }) => {
    await page.route("**/models/signspeak.weights.json", (route) => route.abort());
    await page.goto("/index.html");

    await expect(page.locator("#status")).toHaveAttribute("data-kind", "error", { timeout: 20_000 });
    await expect(page.locator("#status-text")).toContainText("Classifier failed to load");
    await expect(page.locator("#start")).toBeDisabled();
    await expect(page.locator("#glyphgrid .error-note")).toBeVisible();

    // The evidence is independent of the model and must still be there.
    await expect(page.locator("#verdict-value")).toHaveText(/^\d{1,3}\.\d%$/);
  });
});
