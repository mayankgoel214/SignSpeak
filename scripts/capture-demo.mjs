// Drive the real page in Chromium and capture the frames the walkthrough is
// built from. The camera is stubbed with dataset images, because nobody here
// can sign into a webcam; every caption says so.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(HERE, "..");
const OUT = path.join(ROOT, "docs", "frames");
const BASE = process.env.BASE_URL || "http://127.0.0.1:8099";
const WORD = (process.env.WORD || "SIGN").split("");

const fixture = JSON.parse(
  fs.readFileSync(path.join(ROOT, "tests", "fixtures", "browser-cases.json"), "utf8")
);

function imageFor(letter) {
  const c = fixture.cases.find((x) => x.letter === letter);
  if (!c) throw new Error(`no fixture image for ${letter}`);
  return c.png_base64;
}

const STUB = ({ frames, padRatio }) => {
  // One canvas, whose contents the test swaps by setting window.__showLetter.
  window.__frames = frames;
  window.__index = 0;
  navigator.mediaDevices.getUserMedia = async () => {
    const images = await Promise.all(
      frames.map(async (b64) => {
        const img = new Image();
        img.src = `data:image/png;base64,${b64}`;
        await img.decode();
        return img;
      })
    );
    const c = document.createElement("canvas");
    c.width = 640;
    c.height = 480;
    const ctx = c.getContext("2d");
    const draw = () => {
      ctx.fillStyle = "#000";
      ctx.fillRect(0, 0, c.width, c.height);
      const img = window.__index >= 0 ? images[window.__index] : null;
      if (img) {
        const pad = Math.round(Math.max(img.width, img.height) * padRatio);
        const side = Math.max(img.width, img.height) + 2 * pad;
        const scale = Math.min(c.width / side, c.height / side) * 2.4;
        ctx.drawImage(
          img,
          (c.width - img.width * scale) / 2,
          (c.height - img.height * scale) / 2,
          img.width * scale,
          img.height * scale
        );
      }
      requestAnimationFrame(draw);
    };
    draw();
    return c.captureStream(30);
  };
};

const shots = [];
async function shoot(page, name, locator) {
  const file = path.join(OUT, `${name}.png`);
  if (locator) await locator.screenshot({ path: file });
  else await page.screenshot({ path: file });
  shots.push(name);
  console.log(`  ${name}`);
}

const run = async () => {
  fs.rmSync(OUT, { recursive: true, force: true });
  fs.mkdirSync(OUT, { recursive: true });

  // HOST_RESOLVER lets this run against the deployed site from a network whose
  // DNS blocks *.vercel.app, without touching /etc/hosts.
  const args = ["--use-fake-ui-for-media-stream"];
  if (process.env.HOST_RESOLVER) args.push(`--host-resolver-rules=${process.env.HOST_RESOLVER}`);
  const browser = await chromium.launch({ args });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    deviceScaleFactor: 2,
    permissions: ["camera"],
  });
  const page = await context.newPage();
  await page.addInitScript(STUB, {
    frames: WORD.map(imageFor),
    padRatio: fixture.pad_ratio,
  });

  await page.goto(`${BASE}/index.html`);
  await page.locator(".glyphcell").first().waitFor({ timeout: 30_000 });
  await page.evaluate(() => (window.__index = -1));

  await shoot(page, "01-landing");

  await page.locator("#start").click();
  await page.locator('#status[data-kind="ok"]').waitFor({ timeout: 60_000 });

  // Show a hand for this frame. Capturing the instant the camera goes live gives
  // an empty black viewport, which in a walkthrough reads as "it is broken"
  // rather than "nobody is signing yet".
  await page.evaluate(() => (window.__index = 0));
  await page.locator("#letter").filter({ hasNotText: "–" }).waitFor({ timeout: 30_000 });
  await shoot(page, "02-camera-started", page.locator("#device"));

  // Then reset, so the word below starts from an empty buffer whether or not
  // that first sign was held long enough to commit.
  await page.evaluate(() => (window.__index = -1));
  await page.locator("#clear").click();
  await page.waitForTimeout(800);

  // Spell the word one letter at a time, releasing between letters so the same
  // letter twice in a row would still commit.
  for (let i = 0; i < WORD.length; i++) {
    await page.evaluate((n) => (window.__index = n), i);
    await page.locator("#spelled").filter({ hasText: WORD.slice(0, i + 1).join("") }).waitFor({ timeout: 30_000 });
    await shoot(page, `03-letter-${i + 1}-${WORD[i]}`, page.locator("#device"));
    await page.evaluate(() => (window.__index = -1));
    await page.waitForTimeout(500);
  }

  await page.evaluate(() => window.scrollTo(0, 0));
  await shoot(page, "04-verdict", page.locator("#verdict"));
  // `.cards` is the grid and `.card` is a cell, so match the class token exactly
  // rather than as a substring.
  const CARD = "xpath=ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' card ')]";
  await shoot(page, "05-errors", page.locator("#perletter").locator(CARD));
  await shoot(page, "06-matrix", page.locator("#matrix").locator(CARD));
  await shoot(page, "07-alphabet", page.locator("#alphabet .alphabet-layout"));

  // A phone-sized pass, because half the people who open a link open it there.
  const phone = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    permissions: ["camera"],
  });
  const mobile = await phone.newPage();
  await mobile.goto(`${BASE}/index.html`);
  await mobile.locator(".glyphcell").first().waitFor({ timeout: 30_000 });
  await shoot(mobile, "08-mobile", undefined);

  await browser.close();
  fs.writeFileSync(path.join(OUT, "manifest.json"), JSON.stringify(shots, null, 2));
  console.log(`${shots.length} frames in docs/frames`);
};

run().catch((e) => {
  console.error(e);
  process.exit(1);
});
