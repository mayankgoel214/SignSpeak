"""Is the confidence number on the page worth showing, and is the commit
threshold defensible?

The readout displays a percentage beside every letter, and the page commits a
letter only once that percentage has been above 0.7 for half a second. Both were
chosen by hand and neither had ever been measured. A softmax is not a
probability just because it sums to one; a model can be 96% confident and wrong
far more than 4% of the time, and a threshold picked by taste can be rejecting
half the usable frames or none of the bad ones.

This measures both under the honest protocol -- leave-one-signer-out, so every
prediction scored here is on a person the model never trained on -- and writes
eval/calibration.json.

Usage:  python ml/measure_calibration.py
"""

import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataset import load
from model import train

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BINS = np.linspace(0, 1, 11)
THRESHOLDS = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]


def probabilities(model, X, batch=4096):
    out = []
    with torch.no_grad():
        for i in range(0, len(X), batch):
            xb = torch.from_numpy(np.ascontiguousarray(X[i : i + batch], dtype=np.float32))
            out.append(torch.softmax(model(xb), dim=1).numpy())
    return np.concatenate(out)


def main():
    npz = os.path.join(ROOT, "data", "landmarks.npz")
    X, y, signers, classes, _meta = load(npz)

    confidence, correct = [], []
    for s in sorted(set(signers)):
        te = signers == s
        print(f"[fold {s}] training on {(~te).sum()} …", flush=True)
        model = train(X[~te], y[~te], len(classes))
        probs = probabilities(model, X[te])
        confidence.append(probs.max(axis=1))
        correct.append(probs.argmax(axis=1) == y[te])
    confidence = np.concatenate(confidence)
    correct = np.concatenate(correct).astype(float)

    # Reliability: within each confidence band, how often is it actually right?
    reliability, ece = [], 0.0
    for lo, hi in zip(BINS[:-1], BINS[1:]):
        m = (confidence >= lo) & (confidence < hi if hi < 1 else confidence <= 1)
        n = int(m.sum())
        if not n:
            continue
        mean_conf = float(confidence[m].mean())
        accuracy = float(correct[m].mean())
        reliability.append(
            {
                "bin": f"{lo:.1f}–{hi:.1f}",
                "n": n,
                "share": round(n / len(confidence), 4),
                "mean_confidence": round(mean_conf, 4),
                "accuracy": round(accuracy, 4),
                "gap": round(mean_conf - accuracy, 4),
            }
        )
        ece += (n / len(confidence)) * abs(mean_conf - accuracy)

    # What the commit threshold buys and costs.
    thresholds = []
    for t in THRESHOLDS:
        m = confidence >= t
        thresholds.append(
            {
                "threshold": t,
                "frames_kept": round(float(m.mean()), 4),
                "accuracy_of_kept": round(float(correct[m].mean()), 4) if m.any() else None,
                "errors_per_1000_kept": round(float((1 - correct[m].mean()) * 1000), 1) if m.any() else None,
            }
        )

    results = {
        "protocol": "leave-one-signer-out; every prediction is on an unseen person",
        "n_predictions": int(len(confidence)),
        "overall_accuracy": round(float(correct.mean()), 4),
        "mean_confidence": round(float(confidence.mean()), 4),
        "expected_calibration_error": round(float(ece), 4),
        "overconfidence": round(float(confidence.mean() - correct.mean()), 4),
        "reliability": reliability,
        "thresholds": thresholds,
    }

    out = os.path.join(ROOT, "eval", "calibration.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nECE {ece:.4f}   mean confidence {confidence.mean():.4f}   accuracy {correct.mean():.4f}")
    print("\nconfidence band     n      says   actually")
    for r in reliability:
        print(f"  {r['bin']:<12} {r['n']:>7}  {r['mean_confidence']:>6.1%}   {r['accuracy']:>6.1%}")
    print("\nthreshold   kept   accuracy of kept")
    for r in thresholds:
        acc = f"{r['accuracy_of_kept']:.2%}" if r["accuracy_of_kept"] is not None else "-"
        print(f"  {r['threshold']:<8} {r['frames_kept']:>6.1%}   {acc}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
