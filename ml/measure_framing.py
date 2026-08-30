"""How much does framing change detection, and what does that NOT tell us?

The model is measured on the dataset's tight hand crops, padded before detection
the way ml/extract_landmarks.py pads them. The live demo sees something else: a
whole webcam frame in which MediaPipe finds and crops the hand itself. The
question was whether 92.2% is a true statement about an experiment and a
misleading one about the page.

The first version of this script composited each crop into a grey 640x480 frame
and reported that detection collapsed from 99.6% to about 55%. That result was
wrong, and the way it was wrong is the point of keeping this script.

Sweeping background colour against hand size shows the binding variable is the
background, not the size: on black, detection holds at 98-100% at every hand
size; on grey it sits at 59-69% at every hand size. What breaks the palm
detector is the hard rectangular seam where a pasted crop meets a flat field --
an artefact of compositing that no webcam produces.

So this measures MediaPipe's sensitivity to synthetic seams. It does not measure
webcam performance, and no number here should be quoted as if it did. See
docs/framing-experiment.md.

Usage:  python ml/measure_framing.py [n_per_letter]
"""

import json
import os
import random
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

import cv2
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import extract_landmarks as E
from features import normalize
from model import LandmarkMLP

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

FRAME_W, FRAME_H = 640, 480
# Background colour crossed with hand size. Sweeping both is the only reason this
# script says anything trustworthy: with one background it would have looked like
# a finding about hand size, which it is not.
BACKGROUNDS = {"black": 0, "grey": 70}
HAND_HEIGHT_FRACTIONS = (0.25, 0.40, 0.60, 0.80)


def _webcam_frame(img, height_fraction, background, dx, dy):
    """Composite a hand crop into a full frame at a given size and background."""
    scale = (FRAME_H * height_fraction) / img.shape[0]
    hand = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    h, w = hand.shape[:2]
    frame = np.full((FRAME_H, FRAME_W, 3), background, dtype=np.uint8)
    x = int(np.clip((FRAME_W - w) / 2 + dx * FRAME_W, 0, max(0, FRAME_W - w)))
    y = int(np.clip((FRAME_H - h) / 2 + dy * FRAME_H, 0, max(0, FRAME_H - h)))
    frame[y : y + h, x : x + w] = hand[: FRAME_H - y, : FRAME_W - x]
    return frame


def _detect_frame(frame):
    import mediapipe as mp

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = E._get_landmarker().detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    if not result.hand_landmarks:
        return None, None
    pts = np.array([[p.x, p.y, p.z] for p in result.hand_landmarks[0]], dtype=np.float32)
    handed = result.handedness[0][0].category_name if result.handedness else "Right"
    return pts, handed


def _worker(item):
    signer, letter, path, seed = item
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        return None

    out = {"signer": signer, "letter": letter}
    # 1. the framing the model was measured under
    pts, handed = E._detect(path)
    out["cropped"] = (pts.tolist(), handed) if pts is not None else None

    # 2. the framing the demo actually sees
    rng = random.Random(seed)
    for name, background in BACKGROUNDS.items():
        for fraction in HAND_HEIGHT_FRACTIONS:
            frame = _webcam_frame(
                img, fraction, background, rng.uniform(-0.10, 0.10), rng.uniform(-0.10, 0.10)
            )
            pts, handed = _detect_frame(frame)
            out[f"{name}_{fraction}"] = (pts.tolist(), handed) if pts is not None else None
    return out


def main():
    per_letter = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    items_all = E.find_images(os.path.join(ROOT, "data", "dataset5"))
    by_letter = defaultdict(list)
    for signer, letter, path in items_all:
        by_letter[letter].append((signer, path))

    rng = random.Random(20260830)
    work = []
    for letter in sorted(by_letter):
        for i, (signer, path) in enumerate(rng.sample(by_letter[letter], per_letter)):
            work.append((signer, letter, path, rng.randrange(10**6)))
    print(f"{len(work)} images x {1 + len(HAND_HEIGHT_FRACTIONS)} framings", flush=True)

    classes = sorted(by_letter)
    net = LandmarkMLP(len(classes))
    net.load_state_dict(torch.load(os.path.join(ROOT, "models", "signspeak.pt")))
    net.eval()

    def classify(entry):
        pts, handed = entry
        with torch.no_grad():
            feat = torch.from_numpy(normalize(np.array(pts, dtype=np.float32), handed)).unsqueeze(0)
            probs = torch.softmax(net(feat), dim=1)[0]
        idx = int(probs.argmax())
        return classes[idx], float(probs[idx])

    keys = ["cropped"] + [
        f"{name}_{f}" for name in BACKGROUNDS for f in HAND_HEIGHT_FRACTIONS
    ]
    detected = Counter()
    correct = Counter()
    confidence = defaultdict(list)
    by_hand = defaultdict(lambda: [0, 0])

    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2)) as pool:
        for n, row in enumerate(pool.map(_worker, work, chunksize=8)):
            if row is None:
                continue
            for key in keys:
                entry = row.get(key)
                if entry is None:
                    continue
                detected[key] += 1
                predicted, conf = classify(entry)
                hit = predicted == row["letter"]
                correct[key] += hit
                confidence[key].append((conf, hit))
                if key == "cropped":
                    handed = entry[1]
                    by_hand[handed][0] += hit
                    by_hand[handed][1] += 1
            if (n + 1) % 200 == 0:
                print(f"  {n + 1}/{len(work)}", flush=True)

    results = {"n_images": len(work), "framings": {}}
    for key in keys:
        n = detected[key]
        results["framings"][key] = {
            "detection_rate": round(n / len(work), 4),
            "accuracy": round(correct[key] / n, 4) if n else None,
            "n_detected": n,
        }
    results["handedness_cropped"] = {
        h: {"n": total, "accuracy": round(hits / total, 4)} for h, (hits, total) in by_hand.items()
    }
    results["conclusion"] = (
        "Detection tracks the background, not the hand size. A pasted crop on a flat "
        "field leaves a hard rectangular seam that the palm detector does not cope "
        "with; no webcam produces that. These numbers measure compositing, not "
        "webcam performance, and must not be quoted as if they did."
    )

    out = os.path.join(ROOT, "eval", "framing.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)

    print("\nframing              detected   accuracy")
    for key in keys:
        r = results["framings"][key]
        acc = f"{r['accuracy']:.2%}" if r["accuracy"] is not None else "   -  "
        print(f"  {key:<18} {r['detection_rate']:>7.2%}   {acc}")
    print("\nby handedness (cropped framing):")
    for h, r in sorted(results["handedness_cropped"].items()):
        print(f"  {h:<6} n={r['n']:<6} {r['accuracy']:.2%}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
