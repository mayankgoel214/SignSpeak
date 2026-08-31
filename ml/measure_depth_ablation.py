"""Does MediaPipe's z coordinate earn its place in the feature vector?

The features are 21 landmarks x 3 coordinates. The third is MediaPipe's depth
estimate, which is inferred from a single camera rather than measured, and is
widely held to be the least reliable thing the model outputs. Two thirds of the
input being solid and one third being guesswork is worth checking rather than
assuming, in either direction: if z is noise it may be costing accuracy on a new
person, and if it is signal, dropping it would cost more.

Run under leave-one-signer-out so the comparison is on the number that matters,
using the same training code and seed as the real evaluation, so the only
difference between the two arms is the input.

Usage:  python ml/measure_depth_ablation.py
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataset import load
from model import SEED, predict, train

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def loso(X, y, signers, n_classes, label):
    accuracies = {}
    for s in sorted(set(signers)):
        te = signers == s
        model = train(X[~te], y[~te], n_classes, in_dim=X.shape[1])
        acc = float((predict(model, X[te]) == y[te]).mean())
        accuracies[s] = round(acc, 4)
        print(f"  [{label}] fold {s}: {acc:.4f}", flush=True)
    mean = float(np.mean(list(accuracies.values())))
    return {"per_fold": accuracies, "mean": round(mean, 4), "dims": int(X.shape[1])}


def main():
    X, y, signers, classes, _ = load(os.path.join(ROOT, "data", "landmarks.npz"))
    n_classes = len(classes)

    arms = {
        "xyz": X,
        "xy_only": X.reshape(len(X), 21, 3)[:, :, :2].reshape(len(X), 42).copy(),
    }

    results = {"seed": SEED, "protocol": "leave-one-signer-out", "arms": {}}
    for label, features in arms.items():
        print(f"[{label}] {features.shape[1]} dims", flush=True)
        results["arms"][label] = loso(features, y, signers, n_classes, label)

    a, b = results["arms"]["xyz"]["mean"], results["arms"]["xy_only"]["mean"]
    results["difference_points"] = round((a - b) * 100, 2)
    results["verdict"] = (
        "z earns its place" if a - b > 0.002
        else "dropping z is no worse" if abs(a - b) <= 0.002
        else "z is costing accuracy"
    )

    out = os.path.join(ROOT, "eval", "depth-ablation.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nxyz      {a:.4f}\nxy only  {b:.4f}\ndifference {(a - b) * 100:+.2f} points -> {results['verdict']}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
