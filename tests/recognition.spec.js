import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test, expect } from "@playwright/test";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE = path.join(HERE, "fixtures", "browser-cases.json");

// These tests grade the browser against real dataset images. The fixture is not
// committed -- it holds images from a dataset that is not ours to redistribute
// -- so regenerate it with `python ml/make_browser_fixture.py` after
// downloading the dataset. Skipping loudly beats passing vacuously.
const fixture = fs.existsSync(FIXTURE) ? JSON.parse(fs.readFileSync(FIXTURE, "utf8")) : null;

test.describe("the model, in the browser, on real images", () => {
  test.skip(!fixture, `missing ${FIXTURE} — run: python ml/make_browser_fixture.py`);
  test.setTimeout(300_000);

  test("agrees with Python and gets the letters right", async ({ page }) => {
    await page.goto("/index.html");
    await expect(page.locator(".chart-cell")).toHaveCount(24, { timeout: 30_000 });

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
    expect(report.handednessDisagreements).toBe(0);
    expect(report.medianDivergence).toBeLessThan(0.05);
    expect(report.p95Divergence).toBeLessThan(0.25);
    // These are training-set images, so this is a sanity floor on the wiring,
    // not a performance measurement. The performance measurement is
    // eval/results.json.
    expect(report.correct / report.detected).toBeGreaterThan(0.9);
  });
});

test.describe("the live camera path", () => {
  test.skip(!fixture, `missing ${FIXTURE} — run: python ml/make_browser_fixture.py`);
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
    await expect(page.locator("#status")).toHaveText(/Running on your device/, { timeout: 60_000 });
    await expect(page.locator("#stage")).toHaveClass(/live/);

    await expect(page.locator("#letter")).toHaveText(target.letter, { timeout: 30_000 });
    await expect(page.locator("#ranked li")).toHaveCount(3);
    // A steady hand must eventually commit exactly one letter, not a stream of them.
    await expect(page.locator("#spelled")).toHaveText(target.letter, { timeout: 30_000 });

    await page.locator("#backspace").click();
    await expect(page.locator("#spelled")).toHaveText("");
  });
});
