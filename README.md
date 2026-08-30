# SignSpeak

[![ci](https://github.com/mayankgoel214/SignSpeak/actions/workflows/ci.yml/badge.svg)](https://github.com/mayankgoel214/SignSpeak/actions/workflows/ci.yml)

American Sign Language fingerspelling recognised in the browser, on the visitor's
own device. MediaPipe reduces a webcam frame to 21 hand landmarks; a small PyTorch
classifier turns those landmarks into one of 24 letters. There is no server, no
upload, and no per-use cost — the page is static files and the model is 52,000
parameters.

**Live: https://signspeak-asl.vercel.app**

## The number

**92.2% on a signer the model has never seen.**

Measured by leave-one-signer-out cross-validation over the five people in the
Surrey ASL Fingerspelling dataset: train on four, test on the fifth, five times,
so that every one of the 65,522 samples is held out exactly once and no frame of
the test person appears in training. Per-fold accuracy runs from 87.5% to 95.4%.

The same model and the same training code scores **98.7%** on a random 80/20
split. That number is worthless, and it is published here beside the real one on
purpose. Public ASL datasets are frames pulled from a handful of continuous
recording sessions, so neighbouring frames are near-duplicates; a random split
puts those near-duplicates on both sides of the boundary and the model is scored
partly on images it trained on. The 6.5-point gap is what that mistake is worth
on this dataset, and it is small only because the features are landmarks rather
than pixels.

Full protocol, per-letter accuracy, confusion matrix and limitations:
[`docs/EVALUATION.md`](docs/EVALUATION.md), generated from `eval/results.json`
so that no figure in it can drift from the run that produced it.

## Why landmarks and not pixels

A convolutional network trained on 65,000 images of five people's hands learns
those five people, their rooms and their lighting, and there is no amount of
augmentation that fully undoes it. MediaPipe's landmark model was trained on a
vastly larger and more varied corpus than this project could assemble, and it
outputs geometry. Feeding geometry to the classifier means the classifier
*cannot* learn skin tone or background, because it never sees them.

The feature transform then removes everything about a hand except its shape: the
wrist becomes the origin, the hand is rotated so it points up, and it is scaled so
its farthest landmark sits at distance 1. Left hands are mirrored onto right. What
is left is 63 numbers describing a pose.

That transform is also the source of the model's most interesting failure. P and Q
are close to the same hand shape at two different orientations, and rotating
orientation away is precisely what lets the model survive a stranger holding their
wrist at a different angle. The generalisation and the P/Q confusion are one
decision seen from two sides.

## Repository

```
ml/
  features.py             landmark -> 63-dim feature vector (the contract with the browser)
  extract_landmarks.py    dataset images -> data/landmarks.npz, reporting the detection rate
  dataset.py              load the cache and build model inputs
  model.py                the network, and the one training loop used by both scripts below
  evaluate.py             both protocols -> eval/results.json
  train.py                trains on all five signers -> models/signspeak.onnx, verified against PyTorch
  export_web_model.py     folds batch-norm and exports the weights the page loads
  plot_confusion.py       eval/confusion-matrix.png
  write_evaluation_doc.py docs/EVALUATION.md
  make_browser_fixture.py the fixture the browser tests grade themselves against
  tests/                  feature, model and Python/JavaScript parity tests
web/
  index.html style.css    the deployed site: no build step, no framework, no runtime dependencies
  tokens.css              the design tokens -- two colour scales, one type scale, nothing else
  app.js                  camera, inference loop, alphabet reference
  charts.js               every chart, built from eval/results.json at page load
  features.js model.js    the browser halves of ml/features.py and the classifier
scripts/                  build the site, capture the walkthrough, render the social card
models/                   the trained model, its labels, and the MediaPipe hand landmarker
eval/                     results.json and the confusion matrix
```

## Reproducing the number

Requires Python 3.12 and about 5 GB of disk. No GPU: the whole thing trains on a
laptop CPU in a few minutes, which is another consequence of classifying landmarks
instead of images.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# ~2.2 GB, no login required
mkdir -p data && curl -L -o data/fingerspelling5.tar.bz2 \
  https://www.cvssp.org/FingerSpellingKinect2011/fingerspelling5.tar.bz2
tar -xjf data/fingerspelling5.tar.bz2 -C data

.venv/bin/python ml/extract_landmarks.py data/dataset5 data/landmarks.npz  # ~25 min
.venv/bin/python ml/evaluate.py                                            # ~10 min, writes eval/results.json
.venv/bin/python ml/train.py                                               # writes models/
.venv/bin/python ml/export_web_model.py
.venv/bin/python ml/plot_confusion.py
.venv/bin/python ml/write_evaluation_doc.py
```

`evaluate.py` and `train.py` share one training function and one fixed seed, so
the shipped model is trained by the same code that produced the measurement.
Neither reads the test set — no early stopping, no hyperparameter search.

This is reproducible in the strict sense, not the hopeful one: an independent
full re-run of `ml/evaluate.py` — six model trainings, about ten minutes —
reproduces the committed `eval/results.json` **byte for byte, same SHA-256**,
every digit of the confusion matrix included. That was verified by running it,
not inferred from the presence of a seed.

## Running the site

```bash
bash scripts/build-web.sh          # copies the model and eval output into web/
python3 -m http.server 8099 --directory web
```

Then open http://127.0.0.1:8099. The camera needs `localhost` or HTTPS.

## Tests

```bash
.venv/bin/python -m pytest ml/tests -q                    # 33 tests
npm ci && npx playwright install chromium firefox webkit
npx playwright test                                       # 27 tests x 3 engines
```

Chromium, Firefox and WebKit all run the suite. The tests worth knowing about,
because each exists to catch a failure a conventional suite would not:

- **`test_results_integrity.py`** recomputes the published figures from the raw
  confusion matrix — pooled accuracy, per-class accuracy, the top confusions, the
  fold sizes, the leak gap. The 92.2% is quoted in this README, on the live page,
  in the social card and in the generated evaluation document, and all of them
  read one file. If that file is inconsistent with itself the whole story is
  wrong everywhere at once, confidently.
- **`test_shipped_artifacts.py`** checks the three files that each claim to be
  the classifier — the checkpoint, the ONNX export, and the JSON the browser runs
  — against each other. Each is written by a separate script, so any of them can
  go stale silently, and a stale export means the live page runs a model nobody
  measured.
- **`test_feature_parity.py`** and **`test_model_parity.py`** run `features.js`
  and `model.js` under node against their Python originals. The model is trained
  in Python and runs in a browser; if the two drift apart the accuracy figure
  stays true of a model nobody can use. The first caught a real input-shape bug
  the first time it ran.
- **`parity.spec.js`** takes 240 real hands, as landmarks, through the browser's
  own copy of the feature code and the weights, and requires the same letter
  Python reached. 240/240 on all three engines.
- **`failure.spec.js`** drives the ways the camera can fail — refused, absent,
  in use elsewhere, opened-but-silent — and asserts each is reported accurately,
  that the page recovers, and that a failed start does not leave a camera
  running. It also aborts `results.json` and requires the page to show nothing
  rather than a number it invented.
- **`loading.spec.js`** guards behaviour that is invisible when it breaks,
  because the page still works — just slowly and silently: that nothing heavy
  loads before it is wanted, that hovering the button begins the download and
  clicking does not repeat the 8.7 MB, and that a slow download reports honest
  progress.
- **`a11y.spec.js`** runs axe over the idle page, the phone layout and the live
  camera state, plus checks a rule engine cannot make: that a focus ring is
  actually visible on this dark surface, and that every text role clears WCAG AA
  against the surface behind it.
- **`recognition.spec.js`** pushes real dataset *images* through the browser —
  the vendored MediaPipe build, re-detecting the same photograph — and drives the
  page with a stubbed camera to check the hold-and-release rule. These need the
  image fixture and skip, loudly, without it.

WebKit's camera tests are skipped for a measured reason rather than an assumed
one: Playwright's WebKit returns a stubbed `getUserMedia` from the property and
still invokes the native one at call time, which had made a "permission refused"
test pass for entirely the wrong reason. Every other WebKit test runs.

There are two fixtures, and the difference matters. `landmark-cases.json` holds
240 real hands as landmark coordinates plus the letter the Python model predicts
from them; it is committed, because coordinates are derived measurements rather
than the dataset's images, and it keeps `parity.spec.js` running everywhere
including CI. `browser-cases.json` also holds the source photographs, which drive
the full MediaPipe-in-Chromium check; it is **not** committed, because those
images are not mine to redistribute, and the tests that need it skip loudly.

An earlier version of this README claimed the image fixture was not committed
while it was: 3 MB of base64 dataset photographs, present from the first commit
of the rebuild until they were removed. It is untracked and ignored now, and
`ml/tests/test_repository_hygiene.py` fails if it is ever tracked again or if any
committed fixture carries encoded images.

**The history was rewritten on 2026-08-30** to strip that file from every commit,
and `main` was force-pushed. That is a deliberate exception to leaving history
alone: the point was not to make the log look tidy but to stop redistributing
images that are not mine to redistribute. It is worth being precise about what a
rewrite does and does not achieve — the blobs are unreachable from any branch,
but GitHub keeps unreachable objects addressable by their hash until it garbage
collects, and any fork, clone or cache made before the rewrite still has them. So
this reduces the exposure; it does not undo it. The commit hashes of this
repository changed at that point, which is why anything referring to an older one
will not resolve.

## What it costs to load

Measured against the deployed site:

| | |
| --- | --- |
| Idle page | **0.36 MB**, first paint **308 ms**, interactive under a second |
| Starting the camera | **+8.7 MB** — the MediaPipe WebAssembly build and the 7.8 MB hand-landmark model |
| Click to live camera, cold | ~3.8 s on fast wifi, ~38 s throttled to 4 Mbps |
| Click to live camera, after hovering the button | **55 ms** |

Nothing heavy loads until someone shows intent. The download starts on hover,
focus or touch of the start button rather than on the click, so the common case
is already warm and a visitor who never goes near it pays nothing. While it does
download, the model reports true progress against its real uncompressed size —
`Content-Length` is the compressed length on the wire and would run the counter
past 100%, so `scripts/build-web.sh` stamps the real sizes into `assets.json` and
a test checks they match the files actually served.

## Security posture

There is no backend, no account and no user input, so the attack surface is what
the page itself loads. That is worth locking down rather than leaving open
because it happens to be small:

- A strict **Content-Security-Policy**: `default-src 'self'`, no inline scripts,
  no inline styles, `object-src`, `base-uri`, `form-action` and `frame-ancestors`
  all `'none'`. WebAssembly is allowed through `'wasm-unsafe-eval'` specifically,
  rather than a blanket `'unsafe-eval'` on a page with no reason to evaluate
  strings. Enforcing it meant removing every inline style attribute and every
  place markup was built by string concatenation — including one that
  interpolated an error message into HTML.
- **Permissions-Policy** grants `camera=(self)` and denies microphone,
  geolocation, payment and USB outright. The camera is the product; nothing else
  should be reachable.
- `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`,
  `Cross-Origin-Opener-Policy: same-origin`.

`scripts/serve.mjs` replays those headers locally, so the policy is enforced in
development and in CI rather than only on the deployed site — a policy that
applies only in production is a policy nobody tests, and the first sign it is
wrong is a blank page for a visitor. `tests/headers.spec.js` asserts both that
the headers are present and that the page runs clean under them.

## Honest limits

- Five signers is a small population, and the per-fold spread is several points.
- 0.38% of dataset images produce no hand detection and are excluded; the model is
  measured on the images where a hand was found. In the browser this shows up as
  the readout going blank rather than as a wrong letter.
- The training images are cropped, well-lit, single-hand Kinect captures. A laptop
  webcam in a dim room is a harder problem and this evaluation does not measure it.
- Static letters only. **This is not a translator.** ASL is a language with its own
  grammar, and recognising fingerspelled letters is a small corner of it.
- **Nobody has measured this on a real webcam**, including me. Two attempts to
  simulate one by compositing crops into a full frame turned out to measure the
  compositing rather than the camera — [`docs/framing-experiment.md`](docs/framing-experiment.md)
  is the write-up, and it is kept because the first answer was alarming, plausible
  and wrong. What that work does establish is that a hand smaller than about a
  third of the frame is where detection falls away, which is why the page says so.
- **MediaPipe labels almost every hand in this dataset the same way** — 950 of 956
  in a sample. The feature transform mirrors left onto right and a unit test proves
  that mapping is exact, so the other hand works by construction; but that is a
  proof about the transform, not evidence from data.
- The confidence percentage beside a prediction is the model's own softmax
  probability. Measured across held-out signers it is **under**-confident by 3.3
  points — when it claims 96% it is right 99% of the time — which is the safer
  direction and is the label smoothing in the loss doing it deliberately. The full
  reliability table and the commit-threshold trade-off are in
  [`docs/EVALUATION.md`](docs/EVALUATION.md); reproduce with
  `python ml/measure_calibration.py`.

## Credits

- Dataset: N. Pugeault and R. Bowden, *Spelling It Out: Real-Time ASL
  Fingerspelling Recognition*, ICCV 2011 workshops.
  <https://www.cvssp.org/FingerSpellingKinect2011/>
- Hand tracking: [MediaPipe Tasks](https://ai.google.dev/edge/mediapipe), pinned to
  0.10.21 in both Python and JavaScript so the two produce the same landmarks.

MIT licensed. The dataset is not mine and is not redistributed here.
