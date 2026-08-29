"""Run MediaPipe over the Surrey fingerspelling dataset and cache the landmarks.

Every image that MediaPipe cannot find a hand in is counted and reported rather
than dropped quietly: the detection rate is part of the evaluation, because a
model measured only on the frames where detection succeeded is measured on an
easier problem than the one a visitor's webcam poses.

Usage:  python ml/extract_landmarks.py data/dataset5 data/landmarks.npz
"""

import argparse
import os
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TASK_MODEL = os.path.join(HERE, "..", "models", "hand_landmarker.task")

# j and z are absent from this dataset and from every static-image ASL set:
# both letters are defined by movement, so a single frame cannot carry them.
_landmarker = None


def _get_landmarker():
    """One landmarker per worker process; MediaPipe objects are not picklable."""
    global _landmarker
    if _landmarker is None:
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        opts = vision.HandLandmarkerOptions(
            # CPU explicitly: on macOS the default tries a Metal delegate that
            # crashes the process rather than falling back.
            base_options=mp_python.BaseOptions(
                model_asset_path=TASK_MODEL,
                delegate=mp_python.BaseOptions.Delegate.CPU,
            ),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.3,
            min_hand_presence_confidence=0.3,
        )
        _landmarker = vision.HandLandmarker.create_from_options(opts)
    return _landmarker


def _detect(path, pad_ratio=0.6):
    """Returns (21, 3) landmarks and handedness, or (None, None) on no detection.

    The dataset images are tight crops around the hand. MediaPipe's palm
    detector expects some context around the hand and misses a large fraction of
    tight crops, so the image is padded before detection. The ratio was swept on
    a 240-image sample: no padding detects 66.2%, 0.2 detects 95.8%, 0.35 detects
    99.2% and 0.6 detects 100%.
    """
    import mediapipe as mp

    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        return None, None
    h, w = img.shape[:2]
    pad = int(max(h, w) * pad_ratio)
    img = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0))
    # Upscale small crops; the detector has a minimum useful hand size.
    if max(img.shape[:2]) < 384:
        f = 384 / max(img.shape[:2])
        img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = _get_landmarker().detect(mp_image)
    if not result.hand_landmarks:
        return None, None
    lm = result.hand_landmarks[0]
    pts = np.array([[p.x, p.y, p.z] for p in lm], dtype=np.float32)
    handed = result.handedness[0][0].category_name if result.handedness else "Right"
    return pts, handed


def _worker(item):
    signer, letter, path = item
    pts, handed = _detect(path)
    return signer, letter, path, pts, handed


def find_images(root):
    """dataset5/<signer>/<letter>/color_*.png"""
    items = []
    for signer in sorted(os.listdir(root)):
        sdir = os.path.join(root, signer)
        if not os.path.isdir(sdir):
            continue
        for letter in sorted(os.listdir(sdir)):
            ldir = os.path.join(sdir, letter)
            if not os.path.isdir(ldir):
                continue
            for name in sorted(os.listdir(ldir)):
                if name.startswith("color_") and name.endswith(".png"):
                    items.append((signer, letter, os.path.join(ldir, name)))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset_root")
    ap.add_argument("out_npz")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    args = ap.parse_args()

    items = find_images(args.dataset_root)
    if not items:
        sys.exit(f"no images found under {args.dataset_root}")
    print(f"{len(items)} images, {args.workers} workers", flush=True)

    X, y, signers, handedness = [], [], [], []
    missed = Counter()
    total = Counter()

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i, (signer, letter, _path, pts, handed) in enumerate(
            pool.map(_worker, items, chunksize=32)
        ):
            total[(signer, letter)] += 1
            if pts is None:
                missed[(signer, letter)] += 1
            else:
                X.append(pts)
                y.append(letter)
                signers.append(signer)
                handedness.append(handed)
            if (i + 1) % 5000 == 0:
                print(f"  {i + 1}/{len(items)}", flush=True)

    n_total = sum(total.values())
    n_kept = len(X)
    print(f"detected {n_kept}/{n_total} = {100.0 * n_kept / n_total:.2f}%")

    np.savez_compressed(
        args.out_npz,
        landmarks=np.asarray(X, dtype=np.float32),
        labels=np.asarray(y),
        signers=np.asarray(signers),
        handedness=np.asarray(handedness),
        n_images_total=n_total,
        n_detected=n_kept,
        per_class_total=np.asarray([[s, l, total[(s, l)]] for (s, l) in sorted(total)]),
        per_class_missed=np.asarray([[s, l, missed.get((s, l), 0)] for (s, l) in sorted(total)]),
    )
    print(f"wrote {args.out_npz}")


if __name__ == "__main__":
    main()
