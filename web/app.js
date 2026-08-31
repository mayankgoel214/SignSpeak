import { FilesetResolver, HandLandmarker } from "./vendor/mediapipe/vision_bundle.mjs";
import { normalize } from "./features.js";
import { Classifier } from "./model.js";
import { drawSkeleton, layoutPose } from "./hand.js";
import {
  renderComparison,
  renderFolds,
  renderPerLetter,
  renderMatrix,
  renderConfusionList,
  renderCalibration,
  renderThresholds,
} from "./charts.js";

const $ = (id) => document.getElementById(id);
const els = {
  device: $("device"),
  video: $("video"),
  overlay: $("overlay"),
  start: $("start"),
  status: $("status"),
  statusText: $("status-text"),
  letter: $("letter"),
  ring: $("hold-ring"),
  holdHint: $("hold-hint"),
  ranked: $("ranked"),
  spelled: $("spelled"),
  clear: $("clear"),
  backspace: $("backspace"),
  fps: $("fps"),
  delegate: $("delegate"),
  topbar: $("topbar"),
  grid: $("glyphgrid"),
  detailCanvas: $("detail-canvas"),
  detailLetter: $("detail-letter"),
  detailStat: $("detail-stat"),
  detailNote: $("detail-note"),
  verdictValue: $("verdict-value"),
  verdictSub: $("verdict-sub"),
  comparison: $("comparison"),
  folds: $("folds"),
  perletter: $("perletter"),
  matrix: $("matrix"),
  pairs: $("pairs"),
  calibration: $("calibration"),
  calibrationCard: $("calibration-card"),
  calibrationNote: $("calibration-note"),
  thresholds: $("thresholds"),
  readoutHint: $("readout-hint"),
};

// A letter is committed once the same prediction has held for this long above
// the confidence floor. Without it the buffer fills with whatever the hand
// passed through on its way to the sign.
//
// These are milliseconds, not frame counts, and that matters: the loop runs as
// fast as the device can track, so a 12-frame threshold is a fifth of a second
// on a fast laptop and well over a second on a slow phone. The page tells the
// visitor to hold a sign for about half a second, and it should be true of both.
const HOLD_MS = 500;
const RELEASE_MS = 400;
const CONFIDENCE_FLOOR = 0.7;

// How long the camera can see no hand before the page offers advice rather than
// a dash. The advice is specific because it is measured: detection holds at
// 97-100% while the hand is more than about a third of the frame and falls to
// 81% at a quarter of it (docs/framing-experiment.md), so "move closer" is the
// one thing a visitor can usefully do.
const NO_HAND_HINT_MS = 2500;

const RING_CIRCUMFERENCE = 2 * Math.PI * 76;

let landmarker = null;
let classifier = null;
let results = null;
let stream = null;
let running = false;
let lastVideoTime = -1;
let stableLabel = null;
let stableSince = 0;
let lastCommitted = null;
let releaseSince = 0;
let noHandSince = 0;
let frameTimes = [];

/* ------------------------------------------------------------ chrome */

function setStatus(text, kind = "idle") {
  els.statusText.textContent = text;
  els.status.dataset.kind = kind;
}

function setHold(progress) {
  els.ring.style.setProperty("--circ", RING_CIRCUMFERENCE);
  els.ring.style.strokeDashoffset = RING_CIRCUMFERENCE * (1 - Math.min(progress, 1));
}

const observer = new IntersectionObserver(
  ([entry]) => { els.topbar.dataset.stuck = String(!entry.isIntersecting); },
  { rootMargin: "-1px 0px 0px 0px", threshold: 1 }
);
const sentinel = document.createElement("div");
document.body.prepend(sentinel);
observer.observe(sentinel);

/* ------------------------------------------------------------ evidence */

async function loadResults() {
  const res = await fetch("./models/results.json");
  if (!res.ok) throw new Error(`results.json returned ${res.status}`);
  results = await res.json();

  const si = results.signer_independent;
  const d = results.dataset;
  els.verdictValue.textContent = `${(si.mean_accuracy * 100).toFixed(1)}%`;
  els.verdictSub.textContent =
    `${d.n_classes} letters. Every one of ${si.n_test_total.toLocaleString()} landmark samples was held out ` +
    `exactly once, and no frame of the test person appeared in training. MediaPipe found a hand in ` +
    `${(d.detection_rate * 100).toFixed(1)}% of the ${d.images_in_dataset.toLocaleString()} dataset images; ` +
    `the model is measured on those.`;

  const leakage = await fetch("./models/leakage.json")
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);
  renderComparison(els.comparison, results, leakage);
  renderFolds(els.folds, results);
  renderPerLetter(els.perletter, results, { onSelect: selectLetter });
  renderMatrix(els.matrix, results);
  renderConfusionList(els.pairs, results);
  await loadCalibration();
}

// Calibration is measured by a separate script and is optional: if it has not
// been run, the card stays hidden rather than the page inventing a curve.
async function loadCalibration() {
  try {
    const res = await fetch("./models/calibration.json");
    if (!res.ok) return;
    const calibration = await res.json();
    renderCalibration(els.calibration, calibration);
    renderThresholds(els.thresholds, calibration);

    const gap = calibration.overconfidence;
    const direction = gap < 0 ? "under-confident" : "over-confident";
    els.calibrationNote.textContent =
      `Across ${calibration.n_predictions.toLocaleString()} predictions on unseen signers the model is ` +
      `${direction} by ${Math.abs(gap * 100).toFixed(1)} points — it claims ` +
      `${(calibration.mean_confidence * 100).toFixed(1)}% on average and is right ` +
      `${(calibration.overall_accuracy * 100).toFixed(1)}% of the time. ` +
      (gap < 0
        ? "Understating is the safer direction to be wrong in, and it is the label smoothing in the loss doing it on purpose."
        : "Overstating is the dangerous direction, and it is worth knowing before trusting the number beside a letter.") +
      ` Expected calibration error ${(calibration.expected_calibration_error * 100).toFixed(1)}%.`;
    els.calibrationCard.hidden = false;
  } catch {
    // Leave the card hidden.
  }
}

function evidenceFailed(message) {
  els.verdictValue.textContent = "—";
  const note = document.createElement("span");
  note.className = "error-note";
  note.textContent =
    `The measured figures could not be loaded (${message}). ` +
    "Rather than show a number that might be wrong, this section is showing none.";
  els.verdictSub.replaceChildren(note);
  for (const node of [els.comparison, els.folds, els.perletter, els.matrix, els.pairs]) node.innerHTML = "";
}

/* ------------------------------------------------------------ alphabet */

function accuracyFor(letter) {
  const pc = results?.signer_independent?.per_class_accuracy;
  const v = pc?.[letter.toLowerCase()];
  return typeof v === "number" ? v : null;
}

function topConfusionFor(letter) {
  const list = results?.signer_independent?.top_confusions || [];
  return list.find((c) => c.true.toUpperCase() === letter) || null;
}

function drawPose(canvas, pose, opts) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!pose) return;
  drawSkeleton(ctx, layoutPose(pose, canvas.width, canvas.height), opts);
}

function selectLetter(letter) {
  const pose = classifier?.prototypes?.[letter];
  drawPose(els.detailCanvas, pose, {
    lineWidth: 5,
    dotRadius: 6,
    color: "#f5bb64",
    jointColor: "#f3f2ed",
  });
  els.detailLetter.textContent = letter;
  els.detailCanvas.setAttribute("aria-label", `Reference hand pose for the letter ${letter}`);

  const acc = accuracyFor(letter);
  els.detailStat.textContent = acc === null ? "" : `${(acc * 100).toFixed(1)}% correct on a new signer`;

  const confusion = topConfusionFor(letter);
  els.detailNote.textContent = confusion
    ? `Most often mistaken for ${confusion.predicted.toUpperCase()}, on ${(confusion.rate * 100).toFixed(1)}% of all ${letter}.`
    : "Not among the eight most common confusions — whatever it gets wrong, it spreads thinly.";

  for (const cell of els.grid.children) {
    cell.setAttribute("aria-selected", String(cell.dataset.letter === letter));
  }
}

function renderAlphabet() {
  els.grid.innerHTML = "";
  for (const label of classifier.labels) {
    const acc = accuracyFor(label);
    const cell = document.createElement("figure");
    cell.className = "glyphcell";
    cell.dataset.letter = label;
    cell.setAttribute("role", "option");
    cell.setAttribute("tabindex", "0");
    cell.setAttribute("aria-selected", "false");
    // The bar under each cell encodes that letter's measured accuracy, so the
    // reference grid is also a chart.
    if (acc !== null) {
      const t = Math.max(0, Math.min(1, (acc - 0.65) / 0.35));
      cell.style.setProperty("--acc", `color-mix(in srgb, #f5bb64 ${(15 + t * 85).toFixed(0)}%, #34342f)`);
    }

    const canvas = document.createElement("canvas");
    canvas.width = 170;
    canvas.height = 170;
    // The cell's caption already names the letter; an unlabelled canvas beside it
    // is announced as an empty graphic and adds nothing but noise.
    canvas.setAttribute("aria-hidden", "true");
    const caption = document.createElement("figcaption");
    caption.append(document.createTextNode(label));
    const stat = document.createElement("span");
    stat.textContent = acc === null ? "" : `${(acc * 100).toFixed(0)}%`;
    caption.append(stat);
    cell.append(canvas, caption);
    els.grid.append(cell);

    drawPose(canvas, classifier.prototypes[label], {
      lineWidth: 3,
      dotRadius: 3.2,
      color: "#8c8c81",
      jointColor: "#d6d5cd",
    });

    const pick = () => selectLetter(label);
    cell.addEventListener("click", pick);
    cell.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); }
    });
  }
  selectLetter(classifier.labels[0]);
}

/* ------------------------------------------------------------ camera */

// Starting the camera costs about 8.7 MB: the MediaPipe WebAssembly build and the
// hand-landmark model. Measured at 5.2 seconds on fast wifi, and minutes on a
// phone connection -- during which the old code showed one unchanging label, so
// the honest reading of the page was "it is broken".
//
// Two things fix that. The download begins the moment someone shows intent
// (hovers, focuses or touches the button) rather than when they click it, so the
// common case is already warm. And the model's download reports real progress
// against its real uncompressed size, which build-web.sh stamps into
// assets.json -- Content-Length is the *compressed* length on the wire and would
// send the counter past 100%.
const TASK_URL = "./models/hand_landmarker.task";

let trackerPromise = null;

function warmTracker() {
  if (!trackerPromise) trackerPromise = buildTracker().catch((err) => {
    // Swallowed here on purpose: this may be a speculative prefetch nobody asked
    // for. start() retries and reports the failure where it can be seen.
    trackerPromise = null;
    throw err;
  });
  return trackerPromise;
}

async function fetchModel(onProgress) {
  const [res, sizes] = await Promise.all([
    fetch(TASK_URL),
    fetch("./models/assets.json").then((r) => (r.ok ? r.json() : {})).catch(() => ({})),
  ]);
  if (!res.ok) throw new Error(`the hand model failed to load (${res.status})`);

  const expected = sizes["hand_landmarker.task"] || 0;
  if (!res.body) return new Uint8Array(await res.arrayBuffer());

  const reader = res.body.getReader();
  const chunks = [];
  let received = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    received += value.length;
    onProgress(received, expected);
  }
  const buffer = new Uint8Array(received);
  let at = 0;
  for (const chunk of chunks) {
    buffer.set(chunk, at);
    at += chunk.length;
  }
  return buffer;
}

async function buildTracker() {
  setStatus("Loading hand tracker", "busy");
  const fileset = await FilesetResolver.forVisionTasks("./vendor/mediapipe/wasm");

  const modelBuffer = await fetchModel((received, expected) => {
    const mb = (received / 1e6).toFixed(1);
    setStatus(
      expected ? `Loading model ${Math.min(100, Math.round((received / expected) * 100))}%` : `Loading model ${mb} MB`,
      "busy"
    );
  });

  return createLandmarker(fileset, modelBuffer);
}

// The tracker runs on the GPU where there is one. Some machines have no usable
// WebGL -- an old browser, a headless runner, a user who turned it off -- and on
// those the GPU delegate throws at construction and the demo would simply not
// start. Falling back to the CPU keeps it working, more slowly.
//
// The fallback is announced, not silent: the status strip says which delegate is
// in use, so a visitor reading 8 fps can see why.
async function createLandmarker(fileset, modelBuffer) {
  const options = (delegate) => ({
    baseOptions: { modelAssetBuffer: modelBuffer, delegate },
    runningMode: "VIDEO",
    numHands: 1,
    minHandDetectionConfidence: 0.5,
    minHandPresenceConfidence: 0.5,
    minTrackingConfidence: 0.5,
  });

  try {
    const tracker = await HandLandmarker.createFromOptions(fileset, options("GPU"));
    setDelegate("GPU");
    return tracker;
  } catch (err) {
    console.warn("SignSpeak: the GPU delegate is unavailable, falling back to CPU.", err);
    const tracker = await HandLandmarker.createFromOptions(fileset, options("CPU"));
    setDelegate("CPU");
    return tracker;
  }
}

function setDelegate(kind) {
  const value = document.createElement("b");
  value.textContent = `on-device · ${kind}`;
  els.delegate.replaceChildren(document.createTextNode("INFERENCE "), value);
  els.delegate.dataset.delegate = kind;
}

// How long to wait for the first frame before giving up on a stream.
const FIRST_FRAME_TIMEOUT_MS = 8000;

// video.play() is not a reliable signal that a camera is working. It rejects
// when autoplay is blocked even though the stream is fine, and in WebKit it can
// simply never settle for some streams -- which would leave this page stuck on
// "Requesting camera" for ever with the camera light on and no way back. Frames
// arriving is the only thing that actually means the camera is working, so that
// is what is waited on.
function waitForFirstFrame(video) {
  video.play().catch(() => {});
  if (video.readyState >= 2) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const done = (fn) => () => { cleanup(); fn(); };
    const ok = done(resolve);
    const fail = done(() => {
      const err = new Error("the camera stream never produced a frame");
      err.name = "NoFrameError";
      reject(err);
    });
    const timer = setTimeout(fail, FIRST_FRAME_TIMEOUT_MS);
    function cleanup() {
      clearTimeout(timer);
      video.removeEventListener("loadeddata", ok);
      video.removeEventListener("error", fail);
    }
    video.addEventListener("loadeddata", ok, { once: true });
    video.addEventListener("error", fail, { once: true });
  });
}

// A failure has to say what actually went wrong. Reporting everything as
// "permission refused" sends someone to a browser setting that was never the
// problem.
function describeStartFailure(err) {
  switch (err && err.name) {
    case "NotAllowedError":
    case "SecurityError":
      return "Camera permission refused";
    case "NotFoundError":
    case "OverconstrainedError":
      return "No camera found on this device";
    case "NotReadableError":
    case "AbortError":
      return "The camera is in use by another app";
    case "NoFrameError":
      return "Camera opened but sent no video";
    default:
      return `Could not start: ${err && err.message ? err.message : err}`;
  }
}

async function start() {
  els.start.disabled = true;
  let acquired = null;
  try {
    landmarker = await warmTracker();

    setStatus("Requesting camera", "busy");
    acquired = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
    });
    els.video.srcObject = acquired;
    await waitForFirstFrame(els.video);

    stream = acquired;
    acquired = null;
    resetRecognitionState();
    els.overlay.width = els.video.videoWidth || 640;
    els.overlay.height = els.video.videoHeight || 480;
    running = true;
    els.device.dataset.live = "true";
    els.holdHint.textContent = "hold ~0.5s";
    setStatus("Live · nothing uploaded", "ok");
    requestAnimationFrame(loop);
  } catch (err) {
    // Never leave a camera open behind a failure message. By this point the
    // permission may already have been granted and the light already on.
    if (acquired) for (const track of acquired.getTracks()) track.stop();
    els.video.srcObject = null;
    els.start.disabled = false;
    setStatus(describeStartFailure(err), "error");
  }
}

function stop() {
  running = false;
  if (stream) for (const track of stream.getTracks()) track.stop();
  stream = null;
  els.video.srcObject = null;
  els.device.dataset.live = "false";
  els.start.disabled = false;
  els.holdHint.textContent = "";
  resetRecognitionState();
  setHold(0);
  showNoHand();
  setStatus("Camera stopped", "idle");
}

// Everything the loop accumulates while it runs. Leaving any of it behind across
// a stop makes the next session behave on evidence from the last one:
//
//   lastCommitted survived, so the letter you happened to be holding when you
//   stopped could not be spelled after restarting until you dropped your hand --
//   the first letter of the new session silently doing nothing.
//
//   stableSince survived, so a sign already on screen when the camera restarted
//   counted as having been held since before the camera was even on.
//
//   frameTimes survived, so the first frame rate reported after a restart was
//   averaged across however long the camera had been off. The status strip
//   presents that as a measurement.
function resetRecognitionState() {
  stableLabel = null;
  stableSince = 0;
  lastCommitted = null;
  releaseSince = 0;
  noHandSince = 0;
  setNoHandHint(false);
  frameTimes = [];
  els.fps.replaceChildren(document.createTextNode("FPS "), Object.assign(document.createElement("b"), { textContent: "—" }));
}

// The same letter twice in a row is a real word ("HELLO"), so a committed letter
// has to be releasable. Release means the sign stopped being the committed one --
// hand gone, or a different sign, or confidence dropped -- for long enough that
// it was deliberate rather than a flicker.
function trackRelease(now) {
  if (stableLabel === lastCommitted) {
    releaseSince = 0;
    return;
  }
  if (!releaseSince) releaseSince = now;
  if (now - releaseSince >= RELEASE_MS) {
    lastCommitted = null;
    releaseSince = 0;
  }
}

// After the buffer is edited by hand, the sign still in front of the camera must
// not immediately re-commit itself: clearing the buffer while holding a letter
// would refill it instantly. Treating the held sign as already committed means
// the visitor has to release and sign again, which is what they meant.
function suppressRecommit() {
  lastCommitted = stableLabel;
  releaseSince = 0;
}

function commit(label) {
  els.spelled.textContent += label;
  els.spelled.scrollLeft = els.spelled.scrollWidth;
}

function showPrediction(ranked) {
  const top = ranked[0];
  els.letter.textContent = top.label;
  els.letter.dataset.idle = "false";
  els.letter.dataset.committed = String(top.label === lastCommitted);
  // Built as DOM rather than an innerHTML string: the width is a custom property
  // on an element, and an inline style attribute would force the page's content
  // security policy to allow inline styles everywhere.
  els.ranked.replaceChildren(
    ...ranked.slice(0, 3).map((r) => rankedRow(r.label, r.confidence, false))
  );
}

function rankedRow(label, confidence, placeholder) {
  const li = document.createElement("li");
  if (placeholder) li.dataset.placeholder = "true";

  const name = document.createElement("b");
  name.textContent = label;

  const track = document.createElement("span");
  track.className = "track";
  const fill = document.createElement("i");
  fill.style.setProperty("--w", `${(confidence * 100).toFixed(1)}%`);
  track.append(fill);

  const pct = document.createElement("span");
  pct.className = "pct";
  pct.textContent = placeholder ? "—" : `${(confidence * 100).toFixed(0)}%`;

  li.append(name, track, pct);
  return li;
}

function setNoHandHint(show) {
  els.device.dataset.noHand = String(show);
}

function showNoHand() {
  els.letter.textContent = "–";
  els.letter.dataset.idle = "true";
  els.letter.dataset.committed = "false";
  placeholderRanked();
}

// Three inert rows, so the panel has its finished shape before the camera
// starts instead of being a tall empty box that fills in later.
function placeholderRanked() {
  els.ranked.replaceChildren(
    ...Array.from({ length: 3 }, () => rankedRow("–", 0, true))
  );
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
        lm.map((p) => [p.x * els.overlay.width, p.y * els.overlay.height]),
        { lineWidth: 3, dotRadius: 4.5, color: "#f5bb64", jointColor: "#f3f2ed" }
      );

      noHandSince = 0;
      setNoHandHint(false);

      const ranked = classifier.predict(normalize(lm, handedness));
      const top = ranked[0];
      const confident = top.confidence >= CONFIDENCE_FLOOR ? top.label : null;
      if (confident !== stableLabel) {
        stableLabel = confident;
        stableSince = now;
      }

      const held = stableLabel ? now - stableSince : 0;
      if (stableLabel && held >= HOLD_MS && stableLabel !== lastCommitted) {
        commit(stableLabel);
        lastCommitted = stableLabel;
      }
      showPrediction(ranked);
      setHold(stableLabel && stableLabel === lastCommitted ? 1 : held / HOLD_MS);
      trackRelease(now);
    } else {
      showNoHand();
      stableLabel = null;
      stableSince = 0;
      setHold(0);
      trackRelease(now);
      if (!noHandSince) noHandSince = now;
      if (now - noHandSince >= NO_HAND_HINT_MS) setNoHandHint(true);
    }

    frameTimes.push(now);
    while (frameTimes.length > 30) frameTimes.shift();
    if (frameTimes.length > 5) {
      const fps = (frameTimes.length - 1) / ((frameTimes.at(-1) - frameTimes[0]) / 1000);
      const value = document.createElement("b");
      value.textContent = fps.toFixed(0);
      els.fps.replaceChildren(document.createTextNode("FPS "), value);
    }
  }
  requestAnimationFrame(loop);
}

/* ------------------------------------------------------------ wiring */

els.start.addEventListener("click", start);

// Intent, not the click. Someone who never goes near the button never pays for
// the 8.7 MB.
for (const event of ["pointerenter", "focus", "touchstart"]) {
  els.start.addEventListener(event, () => {
    if (!els.start.disabled) warmTracker().catch(() => {});
  }, { once: true, passive: true });
}
els.clear.addEventListener("click", () => {
  els.spelled.textContent = "";
  suppressRecommit();
});
els.backspace.addEventListener("click", () => {
  els.spelled.textContent = els.spelled.textContent.slice(0, -1);
  suppressRecommit();
});

document.addEventListener("keydown", (e) => {
  const typing = ["INPUT", "TEXTAREA"].includes(e.target.tagName);
  if (typing || e.metaKey || e.ctrlKey) return;
  if (e.code === "Space" && e.target.tagName !== "BUTTON") {
    e.preventDefault();
    running ? stop() : (els.start.disabled ? null : start());
  }
  if (e.key === "Backspace" && running) {
    e.preventDefault();
    els.spelled.textContent = els.spelled.textContent.slice(0, -1);
    suppressRecommit();
  }
});

placeholderRanked();
setHold(0);

if (!navigator.mediaDevices?.getUserMedia) {
  setStatus("This browser will not grant camera access", "error");
  els.start.disabled = true;
}

// The evidence and the demo load independently: a failure in one must not take
// the other down, and neither may silently substitute a placeholder. The
// alphabet grid needs both -- the poses from the model, the per-letter
// accuracies from the evidence -- so it waits on the one shared promise rather
// than fetching results.json a second time.
const resultsReady = loadResults().catch((err) => {
  evidenceFailed(err.message);
  return null;
});

Classifier.load("./models/signspeak.weights.json")
  .then(async (loaded) => {
    classifier = loaded;
    await resultsReady;
    renderAlphabet();
  })
  .catch((err) => {
    setStatus(`Classifier failed to load: ${err.message}`, "error");
    els.start.disabled = true;
    const note = document.createElement("p");
    note.className = "error-note";
    // textContent, not innerHTML: an error message is not markup, and building
    // HTML out of one is how a page ends up rendering whatever an error says.
    note.textContent = `The reference poses could not be loaded (${err.message}).`;
    els.grid.replaceChildren(note);
  });
