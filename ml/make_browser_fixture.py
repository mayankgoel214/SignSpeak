"""Build the fixture the browser tests grade themselves against.

Each entry is one dataset image, the letter it really is, the landmarks Python's
MediaPipe found in it, and the letter the trained model predicts from those
landmarks. The browser test re-detects the same image in Chromium, runs its own
copy of the model, and must reach the same letter -- which is the only way to
catch the failure where the model is excellent in Python and the page ships a
different answer.

The fixture is not committed: it contains images from a dataset that is not
mine to redistribute. Regenerate it with this script; the browser tests skip
themselves, loudly, when it is missing.

Usage:  python ml/make_browser_fixture.py [n_per_letter]
"""

import base64
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import torch

import extract_landmarks as E
from features import normalize
from model import LandmarkMLP

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def main():
    per_letter = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    items = E.find_images(os.path.join(ROOT, "data", "dataset5"))
    by_letter = {}
    for signer, letter, path in items:
        by_letter.setdefault(letter, []).append((signer, path))

    classes = sorted(by_letter)
    net = LandmarkMLP(len(classes))
    net.load_state_dict(torch.load(os.path.join(ROOT, "models", "signspeak.pt")))
    net.eval()

    rng = random.Random(20260829)
    out = []
    for letter in sorted(by_letter):
        for signer, path in rng.sample(by_letter[letter], per_letter):
            pts, handed = E._detect(path)
            if pts is None:
                continue
            with torch.no_grad():
                feat = torch.from_numpy(normalize(pts, handed)).unsqueeze(0)
                predicted = classes[int(net(feat).argmax(1))].upper()
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            out.append(
                {
                    "letter": letter.upper(),
                    "signer": signer,
                    "handedness": handed,
                    "python_prediction": predicted,
                    "python_landmarks": [[round(float(v), 6) for v in p] for p in pts],
                    "png_base64": data,
                }
            )

    dest = os.path.join(ROOT, "tests", "fixtures")
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, "browser-cases.json")
    with open(path, "w") as f:
        json.dump({"pad_ratio": 0.6, "cases": out}, f)
    print(f"wrote {path}: {len(out)} cases, {os.path.getsize(path) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
