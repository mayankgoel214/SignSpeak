import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test, expect } from "@playwright/test";
import { WEBKIT_CANNOT_FAKE_A_CAMERA } from "./support/camera.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE = path.join(HERE, "fixtures", "browser-cases.json");

// These tests grade the browser against real dataset images, which means they
// need the image fixture -- and that one is deliberately not committed, because
// the images are not ours to redistribute. Regenerate it with
// `python ml/make_browser_fixture.py` after downloading the dataset. Skipping
// loudly beats passing vacuously.
//
// The parts that do not need pixels live in parity.spec.js, which runs off the
// committed landmark fixture and therefore runs in CI too.
const fixture = fs.existsSync(FIXTURE) ? JSON.parse(fs.readFileSync(FIXTURE, "utf8")) : null;

test.describe("the model, in the browser, on real images", () => {
  test.skip(!fixture, `missing ${FIXTURE} — run: python ml/make_browser_fixture.py`);
  test.setTimeout(300_000);

  test("agrees with Python and gets the letters right", async ({ page }) => {
    await page.goto("/index.html");
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 30_000 });

    const report = await page.evaluate(async ({ cases, padRatio, DELEGATE }) => {
      const { FilesetResolver, HandLandmarker } = await import("./vendor/mediapipe/vision_bundle.mjs");
      const { normalize } = await import("./features.js");
      const { Classifier } = await import("./model.js");

      const fileset = await FilesetResolver.forVisionTasks("./vendor/mediapipe/wasm");
      const landmarker = await HandLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: "./models/hand_landmarker.task", delegate: DELEGATE },
        runningMode: "IMAGE",
        numHands: 1,
        minHandDetectionConfidence: 0.3,
        minHandPresenceConfidence: 0.3,
      });
      const classifier = await Classifier.load("./models/signspeak.weights.json");

      // Reproduce the padding the training pipeline applies, so the detector
      // sees the same framing it saw during extraction.
      async function padded(b64) {
        const img = new Image();
        img.src = `data:image/png;base64,${b64}`;
        await img.decode();
        const pad = Math.round(Math.max(img.width, img.height) * padRatio);
        // Match ml/extract_landmarks.py exactly, upscale included: comparing a
        // 200px browser input against a 384px Python input measures the
        // resolution difference, not the thing this test is for.
        const w = img.width + 2 * pad;
        const h = img.height + 2 * pad;
        const f = Math.max(w, h) < 384 ? 384 / Math.max(w, h) : 1;
        const c = document.createElement("canvas");
        c.width = Math.round(w * f);
        c.height = Math.round(h * f);
        const ctx = c.getContext("2d");
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, c.width, c.height);
        ctx.drawImage(img, pad * f, pad * f, img.width * f, img.height * f);
        return c;
      }

      let detected = 0, correct = 0, handednessDisagreements = 0, agreedWithPython = 0;
      const disagreements = [];
      const divergences = [];
      const wrong = [];
      let worst = null;
      for (const c of cases) {
        const canvas = await padded(c.png_base64);
        const result = landmarker.detect(canvas);
        if (!result.landmarks?.length) continue;
        detected++;

        const handedness = result.handedness?.[0]?.[0]?.categoryName || "Right";
        const browserFeat = normalize(result.landmarks[0], handedness);
        const pythonFeat = normalize(c.python_landmarks, c.handedness);
        let d = 0;
        for (let i = 0; i < browserFeat.length; i++) {
          d = Math.max(d, Math.abs(browserFeat[i] - pythonFeat[i]));
        }
        divergences.push(d);
        if (handedness !== c.handedness) handednessDisagreements++;
        if (!worst || d > worst.divergence) {
          worst = { divergence: d, letter: c.letter, signer: c.signer, pythonHand: c.handedness, browserHand: handedness };
        }

        const predicted = classifier.predict(browserFeat)[0].label;
        if (predicted === c.letter) correct++;
        else wrong.push(`${c.letter}(${c.signer})->${predicted}`);
        if (predicted === c.python_prediction) agreedWithPython++;
        else disagreements.push(`${c.letter}(${c.signer}): python ${c.python_prediction}, browser ${predicted}`);
      }
      divergences.sort((a, b) => a - b);
      const at = (q) => divergences[Math.min(divergences.length - 1, Math.floor(q * divergences.length))];
      return {
        total: cases.length, detected, correct, wrong, worst, handednessDisagreements,
        agreedWithPython, disagreements,
        medianDivergence: at(0.5), p95Divergence: at(0.95), maxDivergence: divergences.at(-1),
      };
    }, { cases: fixture.cases, padRatio: fixture.pad_ratio, DELEGATE: process.env.DELEGATE || "GPU" });

    console.log(
      `browser: detected ${report.detected}/${report.total}, ` +
        `correct ${report.correct}/${report.detected} ` +
        `(${((100 * report.correct) / report.detected).toFixed(1)}%), ` +
        `feature divergence vs Python median ${report.medianDivergence.toFixed(4)} ` +
        `p95 ${report.p95Divergence.toFixed(4)} max ${report.maxDivergence.toFixed(4)}, ` +
        `handedness disagreements ${report.handednessDisagreements}, ` +
        `same letter as Python ${report.agreedWithPython}/${report.detected}`
    );
    if (report.disagreements.length) console.log(`  differed from Python: ${report.disagreements.join("; ")}`);
    console.log(`  worst case: ${JSON.stringify(report.worst)}`);
    if (report.wrong.length) console.log(`  missed: ${report.wrong.join(", ")}`);

    expect(report.detected / report.total).toBeGreaterThan(0.95);
    // The two MediaPipe builds are pinned to the same version, so the features
    // they produce should be all but identical. Bounded at the median and the
    // 95th percentile rather than the maximum: the detector is stochastic and a
    // single frame where it locks on to a slightly different hand pose says
    // nothing, whereas the bulk of the distribution drifting says the page is
    // feeding the model something it was never trained on.
    // What has to hold is that both sides reach the same letter. The landmark
    // coordinates themselves differ slightly and always will: the browser runs
    // the detector on the GPU through WebAssembly and resizes with the canvas,
    // Python runs it on the CPU and resizes with OpenCV. Measured on this
    // fixture, that is worth about 0.02 of median feature drift on CPU and 0.03
    // on GPU, in units where the whole hand spans 1.
    expect(report.agreedWithPython / report.detected).toBeGreaterThan(0.95);
    expect(report.medianDivergence).toBeLessThan(0.05);
    expect(report.p95Divergence).toBeLessThan(0.25);

    // Handedness is a classification, not a fact, and the two MediaPipe builds
    // disagree on a small fraction of frames. It matters because normalize()
    // mirrors left hands onto the right-hand manifold, so a flip hands the model
    // a pose it has never seen. Measured at under 1% here, and two things blunt
    // it in use: MediaPipe smooths handedness across a tracked video rather than
    // deciding per frame, and a letter needs half a second of agreement before
    // it commits, so one bad frame cannot spell anything.
    //
    // This was asserted as exactly zero until a 240-image fixture found two.
    // Zero was an assumption, not a requirement.
    expect(report.handednessDisagreements / report.detected).toBeLessThan(0.02);
    // These are training-set images, so this is a sanity floor on the wiring,
    // not a performance measurement. The performance measurement is
    // eval/results.json.
    expect(report.correct / report.detected).toBeGreaterThan(0.9);
  });
});

test.describe("the live camera path", () => {
  test.skip(!fixture, `missing ${FIXTURE} — run: python ml/make_browser_fixture.py`);
  test.skip(({ browserName }) => browserName === "webkit", WEBKIT_CANNOT_FAKE_A_CAMERA);
  test.setTimeout(180_000);

  test("reads a hand from the camera and spells it", async ({ page }) => {
    // Two images of the same letter, played as a stand-in webcam, must drive the
    // real page: the overlay, the readout and the spelled buffer. This is the
    // path a visitor uses, and none of the tests above touch it.
    const target = fixture.cases.find((c) => c.letter === "L") || fixture.cases[0];

    await page.addInitScript(({ b64, padRatio }) => {
      navigator.mediaDevices.getUserMedia = async () => {
        const img = new Image();
        img.src = `data:image/png;base64,${b64}`;
        await img.decode();
        const pad = Math.round(Math.max(img.width, img.height) * padRatio);
        const c = document.createElement("canvas");
        c.width = 640;
        c.height = 480;
        const ctx = c.getContext("2d");
        const side = Math.max(img.width, img.height) + 2 * pad;
        const scale = Math.min(c.width / side, c.height / side);
        const draw = () => {
          ctx.fillStyle = "#000";
          ctx.fillRect(0, 0, c.width, c.height);
          ctx.drawImage(
            img,
            (c.width - img.width * scale) / 2,
            (c.height - img.height * scale) / 2,
            img.width * scale,
            img.height * scale
          );
          requestAnimationFrame(draw);
        };
        draw();
        return c.captureStream(30);
      };
    }, { b64: target.png_base64, padRatio: fixture.pad_ratio });

    await page.goto("/index.html");
    await page.locator("#start").click();
    await expect(page.locator("#status")).toHaveAttribute("data-kind", "ok", { timeout: 60_000 });
    await expect(page.locator("#device")).toHaveAttribute("data-live", "true");

    await expect(page.locator("#letter")).toHaveText(target.letter, { timeout: 30_000 });
    await expect(page.locator("#ranked li")).toHaveCount(3);
    await expect(page.locator('#ranked li[data-placeholder="true"]')).toHaveCount(0);
    // The panel's idle explainer must give way once there are real predictions
    // to read; it sat there through an entire recorded walkthrough once.
    await expect(page.locator("#readout-hint")).toBeHidden();
    // A steady hand must eventually commit exactly one letter, not a stream of them.
    await expect(page.locator("#spelled")).toHaveText(target.letter, { timeout: 30_000 });

    // Backspace while the sign is still up must not instantly refill the buffer.
    // It did: the letter came straight back, which made this test flaky rather
    // than red and would have been maddening to use.
    await page.locator("#backspace").click();
    await expect(page.locator("#spelled")).toHaveText("");
    await page.waitForTimeout(1500);
    await expect(page.locator("#spelled")).toHaveText("");

    // Space stops the camera, and stopping must actually release the track
    // rather than only changing how the panel looks.
    await page.locator("body").click({ position: { x: 5, y: 5 } });
    await page.keyboard.press("Space");
    await expect(page.locator("#device")).toHaveAttribute("data-live", "false");
    await expect(page.locator("#status")).toHaveText(/Camera stopped/);
    expect(await page.evaluate(() => document.getElementById("video").srcObject)).toBeNull();
  });
});

test.describe("committing letters", () => {
  test.skip(!fixture, `missing ${FIXTURE} — run: python ml/make_browser_fixture.py`);
  test.skip(({ browserName }) => browserName === "webkit", WEBKIT_CANNOT_FAKE_A_CAMERA);
  test.setTimeout(180_000);

  // The hold-and-release rule is the only real product logic in the page, and
  // it has two failure modes that look nothing alike: a held sign repeating
  // itself into the buffer, and a genuine double letter refusing to appear.
  async function driveWith(page, letters) {
    const frames = letters.map((l) => {
      const c = fixture.cases.find((x) => x.letter === l);
      if (!c) throw new Error(`no fixture image for ${l}`);
      return c.png_base64;
    });

    await page.addInitScript(({ frames, padRatio }) => {
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
            const scale = Math.min(c.width / side, c.height / side) * 1.6;
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
    }, { frames, padRatio: fixture.pad_ratio });

    await page.goto("/index.html");
    await page.evaluate(() => (window.__index = -1));
    await page.locator("#start").click();
    await expect(page.locator("#status")).toHaveAttribute("data-kind", "ok", { timeout: 60_000 });
  }

  test("a sign held without release commits exactly once", async ({ page }) => {
    await driveWith(page, ["L"]);
    await page.evaluate(() => (window.__index = 0));
    await expect(page.locator("#spelled")).toHaveText("L", { timeout: 30_000 });

    // Hold it far longer than the commit window. If the release rule is wrong
    // this fills up with L's, and a demo that spells LLLLLL is unusable.
    await page.waitForTimeout(4000);
    await expect(page.locator("#spelled")).toHaveText("L");
  });

  test("the same letter twice in a row still spells twice", async ({ page }) => {
    await driveWith(page, ["L"]);
    await page.evaluate(() => (window.__index = 0));
    await expect(page.locator("#spelled")).toHaveText("L", { timeout: 30_000 });

    await page.evaluate(() => (window.__index = -1));
    await expect(page.locator("#letter")).toHaveText("–", { timeout: 20_000 });
    // Hold the release long enough to be deliberate, the way a person lowering
    // their hand between two letters would.
    await page.waitForTimeout(700);
    await page.evaluate(() => (window.__index = 0));
    await expect(page.locator("#spelled")).toHaveText("LL", { timeout: 30_000 });
  });

  test("no hand means no guess", async ({ page }) => {
    await driveWith(page, ["L"]);
    await expect(page.locator("#letter")).toHaveText("–", { timeout: 20_000 });
    await expect(page.locator("#letter")).toHaveAttribute("data-idle", "true");
    // Placeholder rows, not a confident reading of an empty frame.
    await expect(page.locator('#ranked li[data-placeholder="true"]')).toHaveCount(3);
    await expect(page.locator("#spelled")).toHaveText("");
  });
});
