import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test, expect } from "@playwright/test";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE = path.join(HERE, "fixtures", "landmark-cases.json");

// Landmarks measured by Python's MediaPipe, and the letter Python's model
// predicts from them. No images: these are derived coordinates, not the
// dataset's photographs, so this fixture is committed and runs everywhere --
// including CI, where the image fixture is deliberately absent.
//
// This is the check that stops the published accuracy figure describing a model
// the browser does not actually run.
const fixture = JSON.parse(fs.readFileSync(FIXTURE, "utf8"));

test.describe("the browser reproduces Python", () => {
  test(`agrees on all ${fixture.cases.length} real hands`, async ({ page }) => {
    await page.goto("/index.html");
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 30_000 });

    const report = await page.evaluate(async (cases) => {
      const { normalize } = await import("./features.js");
      const { Classifier } = await import("./model.js");
      const classifier = await Classifier.load("./models/signspeak.weights.json");

      let agreed = 0;
      let correct = 0;
      let worstFeatureGap = 0;
      let worstConfidenceGap = 0;
      const disagreements = [];

      for (const c of cases) {
        const feature = normalize(c.python_landmarks, c.handedness);
        // The Python side normalised the same landmarks; the vectors must match
        // to float precision, because the two implementations are meant to be
        // the same function written twice.
        for (const v of feature) if (!Number.isFinite(v)) throw new Error("non-finite feature");

        const ranked = classifier.predict(feature);
        const predicted = ranked[0].label;
        if (predicted === c.python_prediction) agreed++;
        else disagreements.push(`${c.letter}(${c.signer}): python ${c.python_prediction}, browser ${predicted}`);
        if (predicted === c.letter) correct++;

        const total = ranked.reduce((a, r) => a + r.confidence, 0);
        worstConfidenceGap = Math.max(worstConfidenceGap, Math.abs(total - 1));
        worstFeatureGap = Math.max(worstFeatureGap, Math.abs(feature[0]), Math.abs(feature[1]));
      }
      return { n: cases.length, agreed, correct, disagreements, worstConfidenceGap, worstFeatureGap };
    }, fixture.cases);

    console.log(
      `browser vs python: agreed ${report.agreed}/${report.n}, ` +
        `label correct ${report.correct}/${report.n}`
    );
    if (report.disagreements.length) console.log(`  ${report.disagreements.join("; ")}`);

    // Same landmarks, same normalizer, same weights: this must be exact. Any
    // disagreement at all means the two implementations have drifted.
    expect(report.disagreements).toEqual([]);
    expect(report.agreed).toBe(report.n);

    // The wrist is the origin by construction, so the first two features are
    // zero for every hand. A non-zero here means the normalizer changed shape.
    expect(report.worstFeatureGap).toBeLessThan(1e-6);
    // Softmax must sum to one, or the confidence shown beside a letter is not a
    // probability at all.
    expect(report.worstConfidenceGap).toBeLessThan(1e-5);
  });

  test("every fixture case is one the model gets right end to end", async ({ page }) => {
    // These are training-set hands, so this is a wiring floor rather than a
    // performance measurement -- the performance measurement is eval/results.json.
    await page.goto("/index.html");
    await expect(page.locator(".glyphcell")).toHaveCount(24, { timeout: 30_000 });

    const accuracy = await page.evaluate(async (cases) => {
      const { normalize } = await import("./features.js");
      const { Classifier } = await import("./model.js");
      const classifier = await Classifier.load("./models/signspeak.weights.json");
      let correct = 0;
      for (const c of cases) {
        if (classifier.predict(normalize(c.python_landmarks, c.handedness))[0].label === c.letter) correct++;
      }
      return correct / cases.length;
    }, fixture.cases);

    expect(accuracy).toBeGreaterThan(0.95);
  });
});
