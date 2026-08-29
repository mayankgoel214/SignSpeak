# SignSpeak

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

## Running the site

```bash
bash scripts/build-web.sh          # copies the model and eval output into web/
python3 -m http.server 8099 --directory web
```

Then open http://127.0.0.1:8099. The camera needs `localhost` or HTTPS.

## Tests

```bash
.venv/bin/python -m pytest ml/tests -q   # 10 tests
npm ci && npx playwright install chromium
npx playwright test                      # 6 tests
```

The tests worth knowing about, because they exist to catch failures that a
conventional suite would not:

- **`test_feature_parity.py`** runs `web/features.js` under node against
  `ml/features.py` on random inputs. The model is trained in Python and runs in a
  browser; if the two normalizers drift apart, the accuracy figure stays true of a
  model nobody can use. It caught a real input-shape bug the first time it ran.
- **`test_model_parity.py`** folds a freshly initialised network and checks that
  `web/model.js` reproduces PyTorch's logits. The browser reimplements the forward
  pass by hand rather than shipping an inference runtime, which is only defensible
  if it is checked.
- **`recognition.spec.js`** pushes real dataset images through Chromium — the
  vendored MediaPipe build, the real feature code, the real weights — and requires
  the browser to reach the same letter as Python on at least 95% of them. It also
  drives the actual page with a stubbed camera and asserts that a steady hand
  spells exactly one letter. These skip, loudly, without the fixture; regenerate it
  with `python ml/make_browser_fixture.py` after downloading the dataset.

The fixture is not committed because it contains images from a dataset that is not
mine to redistribute.

## Honest limits

- Five signers is a small population, and the per-fold spread is several points.
- 0.38% of dataset images produce no hand detection and are excluded; the model is
  measured on the images where a hand was found. In the browser this shows up as
  the readout going blank rather than as a wrong letter.
- The training images are cropped, well-lit, single-hand Kinect captures. A laptop
  webcam in a dim room is a harder problem and this evaluation does not measure it.
- Static letters only. **This is not a translator.** ASL is a language with its own
  grammar, and recognising fingerspelled letters is a small corner of it.
- The confidence percentage beside a prediction is the model's own softmax
  probability, which is not the same thing as being right.

## Credits

- Dataset: N. Pugeault and R. Bowden, *Spelling It Out: Real-Time ASL
  Fingerspelling Recognition*, ICCV 2011 workshops.
  <https://www.cvssp.org/FingerSpellingKinect2011/>
- Hand tracking: [MediaPipe Tasks](https://ai.google.dev/edge/mediapipe), pinned to
  0.10.21 in both Python and JavaScript so the two produce the same landmarks.

MIT licensed. The dataset is not mine and is not redistributed here.
