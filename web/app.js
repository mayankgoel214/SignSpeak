import { FilesetResolver, HandLandmarker } from "./vendor/mediapipe/vision_bundle.mjs";
import { normalize } from "./features.js";
import { Classifier } from "./model.js";
import { drawSkeleton, layoutPose } from "./hand.js";

const els = {
  video: document.getElementById("video"),
  overlay: document.getElementById("overlay"),
  start: document.getElementById("start"),
  status: document.getElementById("status"),
  letter: document.getElementById("letter"),
  confidence: document.getElementById("confidence"),
  ranked: document.getElementById("ranked"),
  spelled: document.getElementById("spelled"),
  clear: document.getElementById("clear"),
  backspace: document.getElementById("backspace"),
  chart: document.getElementById("chart"),
  numbers: document.getElementById("numbers"),
  fps: document.getElementById("fps"),
};

// A letter is only committed to the spelled word once the same prediction has
// held for this many consecutive frames above the confidence floor. Without it
// the buffer fills with whatever the hand passed through on its way to the sign.
const HOLD_FRAMES = 12;
const CONFIDENCE_FLOOR = 0.7;
const RELEASE_FRAMES = 8; // frames of a different/absent sign before the same letter can repeat

let landmarker = null;
let classifier = null;
let running = false;
let lastVideoTime = -1;
let stableLabel = null;
let stableCount = 0;
let lastCommitted = null;
let awayCount = 0;
let frameTimes = [];

function setStatus(text, kind = "") {
  els.status.textContent = text;
  els.status.className = `status ${kind}`;
}

async function loadModel() {
  classifier = await Classifier.load("./models/signspeak.weights.json");
  renderChart();
}

async function loadNumbers() {
  // The figures on the page are read from the evaluation output rather than
  // typed into the HTML, so the page cannot claim an accuracy the repository
  // did not measure.
  try {
    const r = await fetch("./models/results.json");
    if (!r.ok) throw new Error(String(r.status));
    const results = await r.json();
    const si = results.signer_independent;
    const rs = results.random_split;
    const d = results.dataset;
    els.numbers.innerHTML = `
      <div class="figure">
        <div class="figure-value">${(si.mean_accuracy * 100).toFixed(1)}%</div>
        <div class="figure-label">accuracy on a signer the model never saw</div>
        <div class="figure-note">Leave-one-signer-out over ${d.signers.length} signers: train on four people,
        test on the fifth, five times. Every one of the ${si.n_test_total.toLocaleString()} samples is held out
        exactly once. Per-fold range ${(si.min_accuracy * 100).toFixed(1)}%–${(si.max_accuracy * 100).toFixed(1)}%,
        which is how much it depends on <em>which</em> person.</div>
      </div>
      <div class="figure muted">
        <div class="figure-value">${(rs.accuracy * 100).toFixed(1)}%</div>
        <div class="figure-label">accuracy if you split the data randomly</div>
        <div class="figure-note">The same model, measured dishonestly. Neighbouring frames of one recording
        land on both sides of a random split, so the model is scored partly on images it trained on.
        The ${(results.leak_gap * 100).toFixed(1)}-point gap is what that mistake is worth.</div>
      </div>
      <div class="figure muted">
        <div class="figure-value">${d.n_classes}</div>
        <div class="figure-label">letters</div>
        <div class="figure-note">The static ASL alphabet. J and Z are absent everywhere in this work:
        both are defined by movement, and a single frame cannot carry them.
        MediaPipe found a hand in ${(d.detection_rate * 100).toFixed(1)}% of the
        ${d.images_in_dataset.toLocaleString()} dataset images; the model is measured on those.</div>
      </div>`;
  } catch (err) {
    els.numbers.innerHTML = `<p class="error">The measured figures could not be loaded (${err.message}).
      Rather than show a number that might be wrong, this section is showing nothing.</p>`;
  }
}

function renderChart() {
  const protos = classifier.prototypes;
  els.chart.innerHTML = "";
  for (const label of classifier.labels) {
    const pose = protos[label];
    const cell = document.createElement("figure");
    cell.className = "chart-cell";
    const canvas = document.createElement("canvas");
    canvas.width = 150;
    canvas.height = 150;
    const caption = document.createElement("figcaption");
    caption.textContent = label;
    cell.append(canvas, caption);
    els.chart.append(cell);
    if (!pose) continue;
    const ctx = canvas.getContext("2d");
    drawSkeleton(ctx, layoutPose(pose, canvas.width, canvas.height), {
      lineWidth: 3,
      dotRadius: 3,
      color: "#64748b",
      jointColor: "#cbd5f5",
    });
  }
}

async function start() {
  els.start.disabled = true;
  try {
    setStatus("Loading the hand tracker…");
    const fileset = await FilesetResolver.forVisionTasks("./vendor/mediapipe/wasm");
    landmarker = await HandLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: "./models/hand_landmarker.task", delegate: "GPU" },
      runningMode: "VIDEO",
      numHands: 1,
      minHandDetectionConfidence: 0.5,
      minHandPresenceConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });

    setStatus("Asking for the camera…");
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
    });
    els.video.srcObject = stream;
    await els.video.play();

    els.overlay.width = els.video.videoWidth || 640;
    els.overlay.height = els.video.videoHeight || 480;
    running = true;
    setStatus("Running on your device. Nothing is uploaded.", "ok");
    document.getElementById("stage").classList.add("live");
    requestAnimationFrame(loop);
  } catch (err) {
    els.start.disabled = false;
    const message =
      err && err.name === "NotAllowedError"
        ? "The camera permission was refused, so there is nothing to read. Allow it and press start again."
        : `Could not start: ${err.message}`;
    setStatus(message, "error");
  }
}

function commit(label) {
  els.spelled.textContent += label;
  els.spelled.scrollLeft = els.spelled.scrollWidth;
}

function showPrediction(ranked) {
  const top = ranked[0];
  els.letter.textContent = top.label;
  els.letter.classList.remove("idle");
  els.letter.classList.toggle("committing", stableCount >= HOLD_FRAMES / 2);
  els.confidence.style.setProperty("--pct", `${(top.confidence * 100).toFixed(1)}%`);
  els.confidence.dataset.value = `${(top.confidence * 100).toFixed(0)}%`;
  els.ranked.innerHTML = ranked
    .slice(0, 3)
    .map(
      (r) =>
        `<li><span>${r.label}</span><span class="bar" style="--w:${(r.confidence * 100).toFixed(1)}%"></span><span class="pct">${(r.confidence * 100).toFixed(0)}%</span></li>`
    )
    .join("");
}

function showNoHand() {
  els.letter.textContent = "–";
  els.letter.classList.remove("committing");
  els.letter.classList.add("idle");
  els.confidence.style.setProperty("--pct", "0%");
  els.confidence.dataset.value = "";
  els.ranked.innerHTML = "";
}

function loop() {
  if (!running) return;
  const now = performance.now();
  if (els.video.currentTime !== lastVideoTime) {
    lastVideoTime = els.video.currentTime;
    const result = landmarker.detectForVideo(els.video, now);
    const ctx = els.overlay.getContext("2d");
    ctx.clearRect(0, 0, els.overlay.width, els.overlay.height);

    if (result.landmarks && result.landmarks.length) {
      const lm = result.landmarks[0];
      const handedness = result.handedness?.[0]?.[0]?.categoryName || "Right";
      drawSkeleton(
        ctx,
        lm.map((p) => [p.x * els.overlay.width, p.y * els.overlay.height])
      );

      const ranked = classifier.predict(normalize(lm, handedness));
      showPrediction(ranked);

      const top = ranked[0];
      if (top.confidence >= CONFIDENCE_FLOOR && top.label === stableLabel) {
        stableCount += 1;
      } else {
        stableLabel = top.confidence >= CONFIDENCE_FLOOR ? top.label : null;
        stableCount = stableLabel ? 1 : 0;
      }
      awayCount = 0;
      if (stableLabel && stableCount === HOLD_FRAMES && stableLabel !== lastCommitted) {
        commit(stableLabel);
        lastCommitted = stableLabel;
      }
    } else {
      showNoHand();
      stableLabel = null;
      stableCount = 0;
      awayCount += 1;
      if (awayCount >= RELEASE_FRAMES) lastCommitted = null;
    }

    frameTimes.push(now);
    while (frameTimes.length > 30) frameTimes.shift();
    if (frameTimes.length > 5) {
      const fps = (frameTimes.length - 1) / ((frameTimes.at(-1) - frameTimes[0]) / 1000);
      els.fps.textContent = `${fps.toFixed(0)} fps`;
    }
  }
  requestAnimationFrame(loop);
}

els.start.addEventListener("click", start);
els.clear.addEventListener("click", () => {
  els.spelled.textContent = "";
  lastCommitted = null;
});
els.backspace.addEventListener("click", () => {
  els.spelled.textContent = els.spelled.textContent.slice(0, -1);
  lastCommitted = null;
});

if (!navigator.mediaDevices?.getUserMedia) {
  setStatus("This browser will not give a page camera access, so the demo cannot run here.", "error");
  els.start.disabled = true;
}

loadNumbers();
loadModel().catch((err) => {
  setStatus(`The classifier failed to load: ${err.message}`, "error");
  els.start.disabled = true;
});
